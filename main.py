import requests
from itertools import count
from pprint import pprint  # debug only


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


def get_all_hh_vacancies(language):
    for page in count():
        page_response = get_hh_vacancies_page(language, page=page)

        if page >= page_response["pages"]:
            break

        yield from page_response["items"]


def predict_rub_salary(vacancy):
    predicted_salary = None
    if not vacancy.get("salary"):
        return
    else:
        salary = vacancy.get("salary")

    if salary.get("currency") != "RUR":
        return

    if salary.get("from") and salary.get("to"):
        predicted_salary = (salary.get("from") + salary.get("to")) / 2
    elif (not salary.get("from")) and salary.get("to"):
        predicted_salary = salary.get("to") * 0.8
    elif salary.get("from") and (not salary.get("to")):
        predicted_salary = salary.get("from") * 1.2

    return predicted_salary


def calculate_avg_salary(vacancies):
    vacancies_processed = 0
    salaries_sum = 0
    for vacancy in vacancies:
        predicted_salary = predict_rub_salary(vacancy)
        if predicted_salary:
            vacancies_processed += 1
            salaries_sum += predicted_salary
    avg_salary = int(salaries_sum/vacancies_processed) if vacancies_processed > 0 else 0
    return avg_salary, vacancies_processed


def main():
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

    for language in top_programming_languages:
        response = get_hh_vacancies_page(language)
        if response["found"] < 100: # magic number
            continue
        language_vacancies[language] = {} # avg_salary_stat
        vacancies = get_all_hh_vacancies(language)
        language_vacancies[language]["vacancies_found"] = response["found"]
        avg_salary, vacancies_processed = calculate_avg_salary(vacancies)
        language_vacancies[language]["average_salary"] = avg_salary
        language_vacancies[language]["vacancies_processed"] = vacancies_processed

    pprint(language_vacancies)


if __name__ == "__main__":
    main()
