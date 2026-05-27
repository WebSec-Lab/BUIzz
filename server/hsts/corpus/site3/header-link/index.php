<?php
    $type = $_GET["type"];
    $decoded = base64_decode($type);
    $header_value = str_replace('https://adition.com/', 'http://adition.com/', $decoded);
    header('Link: ' . $header_value);
    echo $type;
    echo $header_value;
?>

<p id="message">header</p>
