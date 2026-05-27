<?php
$browser_name       = $_COOKIE['browser_name']       ?? $_COOKIE['browser_name1']       ?? $_GET['browser_name']       ?? '';
$number_of_scenario = $_COOKIE['number_of_scenario'] ?? $_COOKIE['number_of_scenario1'] ?? $_GET['number_of_scenario'] ?? '';
$bf                 = $_COOKIE['bf']                  ?? $_COOKIE['bf1']                  ?? $_GET['bf']                 ?? '';
$corpus             = $_COOKIE['corpus']              ?? $_COOKIE['corpus1']              ?? $_GET['corpus']             ?? '';

$tracking = http_build_query(array_filter([
    'browser_name'       => $browser_name,
    'number_of_scenario' => $number_of_scenario,
    'bf'                 => $bf,
    'corpus'             => $corpus,
]));

function t($url) {
    global $tracking;
    if (empty($tracking)) return $url;
    return $url . (strpos($url, '?') !== false ? '&' : '?') . $tracking;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>
    <a id="a1" ping="<?= t('http://adition.com/report/?leak=a-ping') ?>" href="<?= t('http://adition.com/report/?leak=a-href') ?>">CLICKME</a>
</body>
</html>
