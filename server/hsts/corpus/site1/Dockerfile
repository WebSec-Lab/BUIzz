FROM php:7.4-apache

RUN docker-php-ext-install mysqli pdo_mysql
RUN a2enmod rewrite

WORKDIR /var/www/html
