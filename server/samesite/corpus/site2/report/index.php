<?php 
//$servername = "127.0.0.1";
$servername = "host.docker.internal";
$username = "root";
$password = "1234";
$dbname = "diffuserinter"; 
$db_connection_status = "No bug founded";
$report_save_status = "";

$corpus_type = "samesite";  
$leak_data = $_GET["leak"] ?? "default";
$cookie_data = $_SERVER['HTTP_COOKIE'] ?? null;
$scenario_id = $_COOKIE["number_of_scenario1"] ?? $_COOKIE["number_of_scenario"] ?? null;
$browser_name = $_COOKIE["browser_name1"] ?? $_COOKIE["browser_name"] ?? null;
$get_event    = $_COOKIE["bf"] ?? $_COOKIE["bf1"] ?? null;
$corpus       = $_COOKIE["corpus"] ?? $_COOKIE["corpus1"] ?? null;
$interaction  = ($_COOKIE["interaction1"] ?? $_COOKIE["interaction"] ?? null) ?: null;

echo $get_event;

if($get_event == "1"){
    $event_type = "interaction";   
}else{
    $event_type = "corpus";   
}
if (strpos($cookie_data, "strict") !== false) {
    $violation = "strict";
} else if (strpos($cookie_data, "lax") !== false) {
    $violation = "lax";
} else {
    $violation = "none";
}

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
    <title>Report Page</title>
</head>
<body>

    <h2>DB and cookie</h2>
    <p>DB status:<?php echo $db_connection_status ?></p>
    <p>Browser name:<?php echo $browser_name ?></p>
    <p>Cookie info :<?php echo $cookie_data ?></p>
    <p>Leak data: <?php echo $leak_data ?></p>
    <hr>

</body>
</html>