<?php
$valid_policies = ['no-referrer','no-referrer-when-downgrade','origin',
    'origin-when-cross-origin','same-origin','strict-origin',
    'strict-origin-when-cross-origin','unsafe-url'];
$policy = $_GET['policy'] ?? 'no-referrer-when-downgrade';
if (in_array($policy, $valid_policies)) {
    header('Referrer-Policy: ' . $policy);
}
?>
<html>
<head>
    <link rel="prerender" href="to_be_prerendered.html" />
</head>
<body>
<p id='check'>ScriptTest</p>
<script src='script.js'></script>
</body>
</html>
