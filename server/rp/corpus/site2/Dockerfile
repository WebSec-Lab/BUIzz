# PHP 7.4 + Apache
FROM php:7.4-apache

# Install mysqli and PDO MySQL extensions
RUN docker-php-ext-install mysqli pdo_mysql

# Enable Apache mod_rewrite
RUN a2enmod rewrite

# (optional) copy php.ini
# COPY php.ini /usr/local/etc/php/
