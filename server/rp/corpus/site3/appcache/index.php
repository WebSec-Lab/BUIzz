<?php
$valid_policies = ['no-referrer','no-referrer-when-downgrade','origin',
    'origin-when-cross-origin','same-origin','strict-origin',
    'strict-origin-when-cross-origin','unsafe-url'];
$policy = $_GET['policy'] ?? 'no-referrer-when-downgrade';
if (in_array($policy, $valid_policies)) {
    header('Referrer-Policy: ' . $policy);
}
?>
<html manifest='ac.appcache'>
<p id="check">Appcache</p>
</html>
