<?php
$servername = "host.docker.internal";
$username = "root";
$password = "1234";
$dbname = "diffuserinter";
$db_connection_status = "No bug founded";

$corpus_type = "referrer-policy";
$leak_data   = $_GET["leak"] ?? "default";

// Tracking params: cookie takes priority, then URL param, then null
$scenario_id  = $_COOKIE["number_of_scenario1"] ?? $_COOKIE["number_of_scenario"]
             ?? $_GET["scenario_id"] ?? null;
$browser_name = $_COOKIE["browser_name1"] ?? $_COOKIE["browser_name"]
             ?? $_GET["browser_name"] ?? null;
$get_event    = $_COOKIE["bf1"] ?? $_COOKIE["bf"]
             ?? $_GET["bf"] ?? null;
$corpus       = $_COOKIE["corpus1"] ?? $_COOKIE["corpus"]
             ?? $_GET["corpus"] ?? null;
$interaction  = ($_COOKIE["interaction1"] ?? $_COOKIE["interaction"] ?? null) ?: null;

$event_type = ($get_event == "1") ? "interaction" : "corpus";

// RP core: stores the Referer value forwarded by nginx via X-Referer header
$violation = $_SERVER['HTTP_X_REFERER'] ?? "";

$sql = "INSERT INTO event_entry (browser_name, scenario_id, corpus, event_type, corpus_type, leak, violation, interaction) VALUES (?, ?, ?, ?, ?, ?, ?, ?)";

if ($browser_name != null) {
    $conn = new mysqli($servername, $username, $password, $dbname);
    if ($conn->connect_error) {
        $db_connection_status = "Fail: " . $conn->connect_error;
    } else {
        $db_connection_status = "success!";
        $stmt = $conn->prepare($sql);
        if ($stmt) {
            $stmt->bind_param("ssssssss", $browser_name, $scenario_id, $corpus, $event_type, $corpus_type, $leak_data, $violation, $interaction);
            if (!$stmt->execute()) {
                echo "Insert failed: " . $stmt->error;
            } else {
                echo "Insert success!";
            }
            $stmt->close();
        } else {
            echo "Prepare failed: " . $conn->error;
        }
        $conn->close();
    }
} else {
    echo "browser is null";
}
?>

<html>
<head>
    <title>RP Report</title>
</head>
<body>
    <h2>Referrer-Policy Report</h2>
    <p>DB status: <?php echo $db_connection_status ?></p>
    <p>Browser: <?php echo $browser_name ?></p>
    <p>Leak: <?php echo $leak_data ?></p>
    <p>Referer: <?php echo $violation ?></p>
</body>
</html>
