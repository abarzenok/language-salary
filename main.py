import os
from dotenv import load_dotenv
import requests
from itertools import count
from terminaltables import AsciiTable, DoubleTable, SingleTable
from pprint import pprint  # debug only


def print_table(data):
    title = "SJ salaries"

    table_data = [
        ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"],
    ]

    for language in data:
        table_data.append([
            language,
            data[language]["vacancies_found"],
            data[language]["vacancies_processed"],
            data[language]["average_salary"]
        ])

    # AsciiTable.
    table_instance = AsciiTable(table_data, title)
    table_instance.justify_columns[2] = 'right'
    print(table_instance.table)
    print()

    # SingleTable.
    table_instance = SingleTable(table_data, title)
    table_instance.justify_columns[2] = 'right'
    print(table_instance.table)
    print()

    # DoubleTable.
    table_instance = DoubleTable(table_data, title)
    table_instance.justify_columns[2] = 'right'
    print(table_instance.table)
    print()



def get_all_hh_vacancies(language):
    for page in count():
        page_response = get_hh_vacancies_page(
            language,
            page=page
        )

        if page >= page_response["pages"]:
            break

        yield from page_response["items"]


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


def get_sj_vacancies_page(token, language, page):
    superjob_vacancies_api_url = "https://api.superjob.ru/2.0/vacancies/"
    headers = {"X-Api-App-Id": token}
    params = {
        "town": "Moscow",
        "catalogues": 33,  # Разработка, программирование "IT, Интернет, связь, телеком"
        "count": 100,
        "page": page,
        "keywords[0][srws]": 10,
        "keywords[0][skws]": "or",
        "keywords[0][keys]": ["Программист", "Разработчик", "Developer"],
        "keywords[1][srws]": 10,
        "keywords[1][skws]": "particular",
        "keywords[1][keys]": language
    }
    response = requests.get(
        superjob_vacancies_api_url,
        params=params,
        headers=headers,
    )
    response.raise_for_status()

    return response.json()




def get_hh_vacancies_page(language, page=0):
    hh_vacancies_api_url = "https://api.hh.ru/vacancies"
    profession_query = "(Разработчик OR Программист OR Developer) AND {}".format(language)
    response = requests.get(
        hh_vacancies_api_url,
        params={
            "text": profession_query,
            "search_field": "name",
            "page": page,
            "industry": 7,  # magic number
            "professional_role": 96,  # "name": "Программист, разработчик",
            "area": 1, # Moscow
            "period": 30, # Not older than days
        }
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
    predicted_salary = None
    if salary_from and salary_to:
        predicted_salary = (salary_from+salary_to) / 2
    elif (not salary_from) and salary_to:
        predicted_salary = salary_to * 0.8
    elif salary_from and (not salary_to):
        predicted_salary = salary_from * 1.2

    return predicted_salary


def calculate_avg_salary(vacancies, salary_predictor):
    vacancies_processed = 0
    salaries_sum = 0
    for vacancy in vacancies:
        predicted_salary = salary_predictor(vacancy)
        if predicted_salary:
            vacancies_processed += 1
            salaries_sum += predicted_salary
    avg_salary = int(salaries_sum/vacancies_processed) if vacancies_processed > 0 else 0
    return avg_salary, vacancies_processed


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

    language_vacancies = {}


    # for language in top_programming_languages:
    #     response = get_hh_vacancies_page(language)
    #     if response["found"] < 100: # magic number
    #         continue
    #     language_vacancies[language] = {} # avg_salary_stat
    #     vacancies = get_all_hh_vacancies(language)
    #     language_vacancies[language]["vacancies_found"] = response["found"]
    #     avg_salary, vacancies_processed = calculate_avg_salary(vacancies, predict_rub_salary_hh)
    #     language_vacancies[language]["average_salary"] = avg_salary
    #     language_vacancies[language]["vacancies_processed"] = vacancies_processed

    ##sj processing
    for language in top_programming_languages:
        response = get_sj_vacancies_page(api_key_superjob, language=language, page=0)
        # if response["total"] < 100: # magic number sj has too few vacancies
        #     continue
        language_vacancies[language] = {} # avg_salary_stat
        vacancies = get_all_sj_vacancies(api_key_superjob, language=language)
        language_vacancies[language]["vacancies_found"] = response["total"]
        avg_salary, vacancies_processed = calculate_avg_salary(vacancies, predict_rub_salary_sj)
        language_vacancies[language]["average_salary"] = avg_salary
        language_vacancies[language]["vacancies_processed"] = vacancies_processed

    # pprint(language_vacancies)

    print_table(language_vacancies)

    # get_sj_vacancies_page(api_key_superjob, "Python", 0)



if __name__ == "__main__":
    main()
