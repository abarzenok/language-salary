import os
from dotenv import load_dotenv
import requests
from itertools import count
from terminaltables import AsciiTable


def print_table(title, salaries_statistics):
    table_data = [
        [
            "Язык программирования",
            "Вакансий найдено",
            "Вакансий обработано",
            "Средняя зарплата"
        ]
    ]
    for language in salaries_statistics:
        table_data.append(
            [
                language,
                salaries_statistics[language]["vacancies_found"],
                salaries_statistics[language]["vacancies_processed"],
                salaries_statistics[language]["average_salary"]
            ]
        )
    table_instance = AsciiTable(table_data, title)
    print(table_instance.table)
    print()


def get_all_hh_vacancies(language):
    for page in count():
        page_response = get_hh_vacancies_page(
            language,
            page=page
        )
        yield from page_response["items"]
        if page >= page_response["pages"]:
            break


def get_all_sj_vacancies(token, language):
    for page in count():
        page_response = get_sj_vacancies_page(
            token,
            language,
            page=page
        )
        yield from page_response["objects"]
        if not page_response["more"]:
            break


def get_hh_vacancies_page(language, page=0):
    hh_vacancies_api_url = "https://api.hh.ru/vacancies"
    profession_query = "(Разработчик OR Программист OR Developer) AND {}".format(language)
    response = requests.get(
        hh_vacancies_api_url,
        params={
            "text": profession_query,
            "search_field": "name",
            "page": page,
            "industry": 7,
            "professional_role": 96,
            "area": 1,
            "period": 30,
        }
    )
    response.raise_for_status()
    return response.json()


def get_sj_vacancies_page(token, language, page=0):
    superjob_vacancies_api_url = "https://api.superjob.ru/2.0/vacancies/"
    headers = {"X-Api-App-Id": token}
    params = {
        "town": "Moscow",
        "catalogues": 33,
        "count": 100,
        "page": page,
        "keywords[0][srws]": 10,
        "keywords[0][skws]": "or",
        "keywords[0][keys]": ["Программист", "Разработчик", "Developer"],
        "keywords[1][srws]": 10,
        "keywords[1][skws]": "particular",
        "keywords[1][keys]": language,
    }
    response = requests.get(
        superjob_vacancies_api_url,
        params=params,
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def predict_rub_salary_hh(vacancy):
    if not vacancy.get("salary"):
        return
    else:
        salary = vacancy.get("salary")

    if salary.get("currency") != "RUR":
        return

    return predict_salary(
        salary.get("from"),
        salary.get("to")
    )


def predict_rub_salary_sj(vacancy):
    if vacancy.get("currency") != "rub":
        return

    return predict_salary(
        vacancy["payment_from"],
        vacancy["payment_to"]
    )


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif (not salary_from) and salary_to:
        return salary_to * 0.8
    elif salary_from and (not salary_to):
        return salary_from * 1.2


def calculate_avg_salary(vacancies, salary_predictor):
    vacancies_processed = 0
    salaries_sum = 0
    for vacancy in vacancies:
        predicted_salary = salary_predictor(vacancy)
        if not predicted_salary:
            continue
        vacancies_processed += 1
        salaries_sum += predicted_salary
    avg_salary = (
        int(salaries_sum / vacancies_processed)
        if vacancies_processed > 0 else 0
    )
    return avg_salary, vacancies_processed


def get_hh_statistics(languages):
    languages_statistics = {}
    for language in languages:
        response = get_hh_vacancies_page(language)
        if response["found"] < 100:
            continue
        languages_statistics[language] = {}
        vacancies = get_all_hh_vacancies(language)
        languages_statistics[language]["vacancies_found"] = response["found"]
        avg_salary, vacancies_processed = calculate_avg_salary(
            vacancies,
            predict_rub_salary_hh
        )
        languages_statistics[language]["average_salary"] = avg_salary
        languages_statistics[language]["vacancies_processed"] = vacancies_processed
    return languages_statistics


def get_sj_statistics(token, languages):
    languages_statistics = {}
    for language in languages:
        response = get_sj_vacancies_page(
            token,
            language,
        )
        if not response["total"]:
            continue
        languages_statistics[language] = {}
        vacancies = get_all_sj_vacancies(
            token,
            language=language
        )
        languages_statistics[language]["vacancies_found"] = response["total"]
        avg_salary, vacancies_processed = calculate_avg_salary(
            vacancies,
            predict_rub_salary_sj
        )
        languages_statistics[language]["average_salary"] = avg_salary
        languages_statistics[language]["vacancies_processed"] = vacancies_processed
    return languages_statistics


def main():
    load_dotenv()
    api_key_superjob = os.getenv("API_KEY_SUPERJOB")
    top_programming_languages = [
        "Javascript",
        "Python",
        "Java",
        "TypeScript",
        "C#",
        "PHP",
        "C++",
        "Shell",
        "C",
        "Ruby",
        "Scala",
        "Golang",
    ]

    print_table(
        "HeadHunter Moscow",
        get_hh_statistics(top_programming_languages)
    )

    print_table(
        "SuperJob Moscow",
        get_sj_statistics(
            api_key_superjob,
            top_programming_languages
        )
    )


if __name__ == "__main__":
    main()
