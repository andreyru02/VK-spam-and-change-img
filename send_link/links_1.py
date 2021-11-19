from time import sleep
import json
import requests
from python_rucaptcha import ImageCaptcha


class ErrorPassword(Exception):
    """Для вызова исключения при смене пароля владельцем аккаунта"""
    pass


class ErrorBan(Exception):
    """Для вызова исключения при блокировке аккаунта"""
    pass


def read_token():
    """
    Чтение файла с данными авторизации token.txt
    :return ['login1:password1:token1', 'login2:password2:token3', ...]
    """
    with open('token.txt', encoding='utf-8') as file:
        auth_data = file.readlines()

    print('[INFO] Данные из файла token.txt прочитаны.')

    return auth_data


def get_user_info(token, headers, proxies):
    """
    Получаем информацию о пользователе
    :return ['first_name', 'last_name', 'user_id']
    """
    method = 'https://api.vk.com/method/account.getProfileInfo'
    params = {
        'access_token': token,
        'v': '5.131'
    }
    header = {'User-Agent': headers}

    try:
        resp = requests.get(method, params=params, headers=header, proxies=proxies)
        resp_json = resp.json()

        print(resp_json)

        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            user_info = []
            first_name = resp_json.get('response').get('first_name')
            last_name = resp_json.get('response').get('last_name')
            user_id = resp_json.get('response').get('id')
            user_info.append(user_id)
            user_info.append(first_name)
            user_info.append(last_name)
            print(f'[INFO] Данные пользователя: {first_name} {last_name}')
            return user_info

    except Exception as err:
        print(f'[ERROR] Произошла ошибка при получении данных пользователя.\n'
              f'{err}')
        print(resp_json)


def get_friends(token, headers, proxies):
    """
    Получаем список друзей
    :return: [id1, id2, id3, ...]
    """

    method = 'https://api.vk.com/method/friends.get'
    params = {
        'access_token': token,
        'v': '5.131'
    }
    header = {'User-Agent': headers}

    try:
        print('[INFO] Получение списка друзей.')
        resp = requests.get(method, params=params, headers=header, proxies=proxies)
        resp_json = resp.json()

        print(resp_json)

        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            print('[INFO] Список друзей получен.')
            return resp_json.get('response').get('items')
    except Exception as err:
        print('[ERROR] Возникла ошибка при получение списка друзей.\n'
              f'{err}')


def send_me_msg(user_id, token, msg_txt, msg_link, headers, proxies):
    method = 'https://api.vk.com/method/messages.send'
    edit_method = 'https://api.vk.com/method/messages.edit'

    try:
        params = {
            'user_id': int(user_id),
            'random_id': 0,
            'message': f'{msg_txt}{msg_link}',
            'dont_parse_links': 0,
            'access_token': token,
            'v': '5.131'
        }

        header = {'User-Agent': headers}

        # Отправка сообщения себе
        resp = requests.post(url=method, params=params, headers=header, proxies=proxies).json()
        id_msg = resp.get('response')

        edit_params = {
            'peer_id': int(user_id),
            'message': msg_txt,
            'message_id': id_msg,
            'keep_snippets': 1,
            'access_token': token,
            'v': '5.131'
        }

        if 'response' in resp:
            print('[INFO] Сообщение для рассылки отправлено.')
            # return id_msg
        elif 'error' in resp:
            if resp.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_sid = resp.get('error').get('captcha_sid')
                captcha_img = resp.get('error').get('captcha_img')
                captcha_key = captcha_solution(captcha_img)
                captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
                resp = requests.get(method, params={**params, **captcha_send}, headers=header, proxies=proxies)
                if resp.status_code == requests.codes.ok and 'response' in resp.json():
                    print('[INFO] Сообщение отправлено.')
                    # return id_msg
        else:
            print('[ERROR] Сообщение не отправлено.')
            print(resp.json())

    except Exception as err:
        print('Возникла ошибка при отправке сообщения.\n'
              f'{err}')

    sleep(5)
    # редактирование сообщения (удаление ссылки из текста)
    try:
        edit_msg_resp = requests.post(url=edit_method, params=edit_params, headers=header, proxies=proxies).json()
        if 'response' in edit_msg_resp:
            print('[INFO] Сообщение для рассылки отредактировано.')
            return id_msg
        elif 'error' in resp:
            if resp.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_sid = resp.get('error').get('captcha_sid')
                captcha_img = resp.get('error').get('captcha_img')
                captcha_key = captcha_solution(captcha_img)
                captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
                edit_msg_resp = requests.get(edit_method, params={**edit_params, **captcha_send},
                                             headers=header, proxies=proxies)
                if edit_msg_resp.status_code == requests.codes.ok and 'response' in edit_msg_resp.json():
                    print('[INFO] Сообщение отредактировано.')
                    return id_msg
        else:
            print('[ERROR] Сообщение не отредактировано.')
            print(resp.json())
    except Exception as err:
        print('Возникла ошибка при редактировании сообщения.\n'
              f'{err}')


def send_msg(friend, forward_msg, token, headers, proxies):
    """Рассылка сообщений"""
    method = 'https://api.vk.com/method/messages.send'
    method_delete_msg = 'https://api.vk.com/method/messages.delete'
    params_def = {
        'user_id': friend,
        'random_id': 0,
        'forward_messages': forward_msg,
        'access_token': token,
        'v': '5.131'
    }
    header = {'User-Agent': headers}

    try:
        print('[INFO] Выполняется рассылка сообщений.')
        resp = requests.get(method, params=params_def, headers=header, proxies=proxies).json()
        print(resp)

        if 'response' in resp:
            print('[INFO] Сообщение отправлено.')
            message_id = resp.get('response')
            params_delete_msg = {
                'message_ids': message_id,
                'access_token': token,
                'v': '5.131'
            }

            resp_del_msg = requests.get(method_delete_msg, params_delete_msg, headers=header, proxies=proxies).json()
            if 'response' in resp_del_msg:
                print('[INFO] Сообщение удалено.')
            else:
                print('[ERROR] Возникла ошибка при удалении сообщения.\n'
                      f'{resp_del_msg}')

        elif 'error' in resp:
            if resp.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_sid = resp.get('error').get('captcha_sid')
                captcha_img = resp.get('error').get('captcha_img')
                captcha_key = captcha_solution(captcha_img)
                captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
                resp = requests.get(method, params={**params_def, **captcha_send}, headers=header, proxies=proxies)
                if resp.status_code == requests.codes.ok and 'response' in resp:
                    print('[INFO] Сообщение отправлено.')
            elif resp.get('error').get('error_code') == 5:
                if 'invalid session' in resp.get('error').get('error_msg'):
                    print('[ERROR] Аккаунт невалид. Возможно владелец сменил пароль.')
                    raise ErrorPassword
                elif 'user is blocked' in resp.get('error').get('error_msg'):
                    print('[ERROR] Аккаунт заблокирован!')
                    raise ErrorBan
        else:
            print('[ERROR] Сообщение не отправлено.')
            print(resp.json())
    except Exception as err:
        print('[ERROR] Возникла ошибка при отправке сообщения или удалении.\n'
              f'{err}')


def captcha_solution(captcha_img):
    """
    Решение капчи
    :return: captcha_key
    """
    break_count = 3
    while break_count > 0:
        with open('captcha.txt', encoding='utf-8') as file:
            rucaptcha_key = file.readline()
        # Ссылка на изображения для расшифровки
        image_link = captcha_img
        # Возвращается JSON содержащий информацию для решения капчи
        user_answer = ImageCaptcha.ImageCaptcha(rucaptcha_key=rucaptcha_key).captcha_handler(captcha_link=image_link)

        if not user_answer['error']:
            # решение капчи
            print('[INFO] Капча решена.')
            # captcha_resp = {'captcha_sid': user_answer['taskId'], 'captcha_key': user_answer['captchaSolve']}
            return user_answer['captchaSolve']
        elif user_answer['error']:
            break_count -= 1
            print('[ERROR] Ошибка при решении капчи. Повтор.')
            print(user_answer['errorBody'])


def sort_online(user_ids, token, headers, proxies):
    """
    Сортирует пользователей online, offline
    :return: [[online_id1, online_id2, ...], [offline_id1, offline_id2, ...]]
    """

    method = 'https://api.vk.com/method/users.get'
    users_list = []
    online = []
    offline = []

    try:
        print('[INFO] Выполняется сортировка друзей по онлайну.')

        params_def = {
            'user_ids': ', '.join(map(str, user_ids)),
            'fields': 'online',
            'access_token': token,
            'v': '5.131'
        }
        header = {'User-Agent': headers}
        resp = requests.get(method, params=params_def, headers=header, proxies=proxies).json()
        # print(resp)
        if 'response' in resp:
            # если онлайн (1) - в список online
            for user in resp.get('response'):
                if user.get('online') == 1:
                    online.append(user.get('id'))
                elif user.get('online') == 0:
                    offline.append(user.get('id'))
        elif 'error' in resp:
            if resp.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_sid = resp.get('error').get('captcha_sid')
                captcha_img = resp.get('error').get('captcha_img')
                captcha_key = captcha_solution(captcha_img)
                captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
                resp = requests.get(method, params={**params_def, **captcha_send}, headers=header,
                                    proxies=proxies).json()
                if resp.status_code == requests.codes.ok and 'response' in resp:
                    print('[INFO] Повторный запрос на получение статусов онлайна отправлен.')
        users_list.append(online)
        users_list.append(offline)
        print('[INFO] Сортировка друзей по онлайну выполнена.')
        return users_list

    except Exception as err:
        print('[ERROR] Возникла ошибка при получении статусов онлайна.\n'
              f'{err}')


def read_headers():
    with open('user-agents.txt', encoding='utf-8') as file:
        headers = file.readlines()

    print('[INFO] Данные из файла user_agents.txt прочитаны.')

    return headers


def main():
    with open('input_data.json', encoding='utf-8') as file:
        data = json.load(file)
        wait = data.get('data').get('wait')
        message_txt = data.get('data').get('message_txt')
        link = data.get('data').get('link')

    auth_data = read_token()
    read_header = read_headers()

    count_account = 1
    for auth in auth_data:
        for header in read_header:
            auth_data_list = auth.strip('\n').split(':')

            with open('proxy.txt', encoding='utf-8') as file:
                proxy = file.readline().replace('\n', '')

            with open('proxy.txt', 'r') as f:
                lines = f.readlines()

            with open('proxy.txt', 'w') as f:
                f.writelines(lines[1:])

            proxies = {
                "http": f"http://{proxy}",
                "https": f"http://{proxy}"
            }

            token = auth_data_list[2]
            headers = header.strip('\n')

            user_info = get_user_info(token, headers=headers, proxies=proxies)
            friends = get_friends(token, headers=headers, proxies=proxies)
            if len(friends) > 1000:
                friends = friends[:1000]
            sleep(3)
            sort_friends = sort_online(friends, token, headers=headers, proxies=proxies)
            id_msg = send_me_msg(user_id=user_info[0], token=token, msg_txt=message_txt, msg_link=link,
                                 headers=headers, proxies=proxies)

            count_friends = 0

            print('[INFO] Выполняется рассылка по онлайн пользователям.')
            for friend in sort_friends[0]:
                send_msg(friend=friend, forward_msg=id_msg, token=token, headers=headers, proxies=proxies)
                count_friends += 1
                print(f'[INFO] Сообщение {count_friends} из {len(sort_friends[0])}.\n'
                      f'[INFO] Аккаунт {count_account} из {len(auth_data)}.\n'
                      f'Пауза на {wait} секунд.')
                if count_friends == 300:
                    print('[INFO] Достигнут лимит сообщений. Переходим к следующему аккаунту.')
                    break
                sleep(wait)

            print('[INFO] Выполняется рассылка по оффлайн пользователям.')
            for friend in sort_friends[1]:
                try:
                    send_msg(friend=friend, forward_msg=id_msg, token=token, headers=headers, proxies=proxies)
                    count_friends += 1
                    print(f'[INFO] Сообщение {count_friends} из {len(sort_friends[1])}.\n'
                          f'[INFO] Аккаунт {count_account} из {len(auth_data)}.\n'
                          f'Пауза на {wait} секунд.')
                    if count_friends == 300:
                        print('[INFO] Достигнут лимит сообщений. Переходим к следующему аккаунту.')
                        break
                    sleep(wait)
                except ErrorPassword:
                    continue
                except ErrorBan:
                    raise Exception('Аккаунт заблокирован. Работа скрипта остановлена!')

            count_account += 1


if __name__ == '__main__':
    main()
