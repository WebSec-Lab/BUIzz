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
<html>

<p id="check">interactive</p>

<a id="a1" ping="<?= t('https://adition.com/report/?leak=a-ping') ?>" href="<?= t('https://adition.com/report/?leak=a-href') ?>">CLICKME</a>


<hr>

<img id="i1" src="black.jpg" width="145" height="126" usemap="#map">
<map name="map">
<area ping="<?= t('https://adition.com/report/?leak=area-ping') ?>" shape="rect" coords="0,0,150,150" href="#">
</map>

<hr>

<img id="i2" src="black.jpg" width="145" height="126" longdesc="<?= t('https://adition.com/report/?leak=img-longdesc') ?>">

<hr>

<form id="f1"></form><button id="b1" form="f1" formaction="<?= t('https://adition.com/report/?leak=button-formaction') ?>">CLICKME</button>

<hr>

<isindex id="index2" action="<?= t('https://adition.com/report/?leak=isindex-action') ?>"></isindex>

<form id="from123"></form><isindex id="index1" type="submit" formaction="<?= t('https://adition.com/report/?leak=isindex-formaction') ?>" form="form123"></isindex>

<hr>

<p id="p1" contextmenu="a">Right Click</p>
<menu type="context" id="a">
    <menuitem id="menu-item" label="a" icon="<?= t('https://adition.com/report/?leak=menuitem-icon') ?>"></menuitem>
</menu>

<hr>

<svg version="1.1" xmlns="https://www.w3.org/2000/svg" xmlns:xlink="https://www.w3.org/1999/xlink">
    <a id="s1" xlink:href="<?= t('https://adition.com/report/?leak=svg-a-text/') ?>"><text transform="translate(0,20)">CLICKME</text></a>
</svg>

<hr>

<math id="m1" xlink:href="<?= t('https://adition.com/report/?leak=mathml-math') ?>">CLICKME</math>

<hr>

<math id="m2"><mi xlink:href="<?= t('https://adition.com/report/?leak=mathml-mi') ?>">CLICKME</mi></math>

</html>
