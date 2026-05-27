<?php
$servername = "host.docker.internal";
$username = "root";
$password = "1234";
$dbname = "diffuserinter";
$db_connection_status = "No bug founded";

$corpus_type = "hsts";
$leak_data = $_GET["leak"] ?? "default";
$scenario_id  = $_COOKIE["number_of_scenario1"] ?? $_COOKIE["number_of_scenario"]
             ?? $_GET["number_of_scenario"] ?? null;
$browser_name = $_COOKIE["browser_name1"] ?? $_COOKIE["browser_name"]
             ?? $_GET["browser_name"] ?? null;
$get_event    = $_COOKIE["bf1"] ?? $_COOKIE["bf"]
             ?? $_GET["bf"] ?? null;
$corpus       = $_COOKIE["corpus1"] ?? $_COOKIE["corpus"]
             ?? $_GET["corpus"] ?? null;
$interaction  = ($_COOKIE["interaction1"] ?? $_COOKIE["interaction"] ?? null) ?: null;

if($get_event == "1"){
    $event_type = "interaction";
}else{
    $event_type = "corpus";
}
$violation = $_SERVER['HTTP_X_FORWARDED_PROTO'] ?? "unknown";

$sql = "INSERT INTO event_entry (browser_name, scenario_id, corpus, event_type, corpus_type, leak, violation, interaction) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ";
if($browser_name!=null){
    $conn = new mysqli($servername, $username, $password, $dbname);
    if ($conn->connect_error) {
        $db_connection_status = "Fail:" . $conn->connect_error;
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
    }
}else{
    echo "browser is null";
}
?>

<html>
<head>
    <title>HSTS Report</title>
</head>
<body>
    <h2>HSTS Report</h2>
    <p>DB: <?php echo $db_connection_status ?></p>
    <p>Proto: <?php echo $violation ?></p>
    <p>Leak: <?php echo $leak_data ?></p>
</body>
</html>
