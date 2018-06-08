# Установка хостинга на голый сервер
Инструкция по установка окружения для сайтов на PHP/MySQL

## Пользователи
### Создание пользователя
```
$ adduser -m {username}
```
Опция **-m** создает домашнюю директорию пользователя.
Далее вас попросят ввести пароль для нового пользователя.
Пользователь будет принадлежать группе с именем пользователя (username : username), чтобы добавить пользователя в уже существующую группу нужно добавить **" -g {groupname}"**

### Добавление в sudoers

Если установлен _sudoers_, то окрываем файл настроек:
```
$ sudo visudo
```
Ищем там строчку 
```
# User privilege specification
root   ALL=(ALL:ALL) ALL
```
В списке после неё добавляем строку о нашем пользователе
```
{username}      ALL=(ALL:ALL) ALL
```
Если хотим, чтобы при использовании **sudo** не требовалось вводить пароль, то
```
{username}      ALL=(ALL) NOPASSWD:ALL
```
Сохраняем файл.

### Настройка авторизации по ssh ключу

1. На локальной машине через терминал создаем пару публичный+закрытый ключ
```
$ ssh-keygen
```
2. Переименовываем созданные файлы
+ id_rsa -> project_name.pem
+ id_rsa.pub -> project_name.pub

3. На сервере откываем файл с ssh ключами пользователя
```
$ sudo nano [user_home_dir_path]/.ssh/authorized_keys
```
и добавляем в него содержимое файла project_name.pub (после этого можно удалить этот файл с локальной машины)

4. После того как убедимся, что авторизация по ключу работает, можно отключить авторизацию по паролю. В файле _/etc/ssh/sshd_config_ ставим **PasswordAuthentication no**. Чтобы изменение конфига вступили в силу:
```
$ sudo systemctl reload sshd
```

## Apache, PHP, MySQL
```
$ sudo apt-get update

$ sudo apt-get install apache2

$ sudo apt-get install mysql-server
$ sudo mysql_secure_installation

$ sudo apt install php
```
