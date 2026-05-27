<?php 
//$servername = "127.0.0.1";
$servername = "host.docker.internal";
$username = "root";
$password = "1234";
$dbname = "diffuserinter"; 
$db_connection_status = "No bug founded";
$report_save_status = "";

$corpus_type = "hsts";  
$leak_data = $_GET["leak"] ?? "default";
$cookie_data = $_SERVER['HTTP_COOKIE'] ?? null;
$scenario_id = $_COOKIE["number_of_scenario1"] ?? $_COOKIE["number_of_scenario"] ?? null;
$browser_name = $_COOKIE["browser_name1"] ?? $_COOKIE["browser_name"] ?? null;
$get_event = $_COOKIE["bf"] ?? $_COOKIE["bf1"] ?? null;
$corpus = $_COOKIE["corpus"] ?? $_COOKIE["corpus1"] ?? null;

echo $get_event;

if($get_event == "1"){
    $event_type = "interaction";   
}else{
    $event_type = "corpus";   
}
$violation = $_SERVER['HTTP_X_FORWARDED_PROTO'];

$sql = "INSERT INTO event_entry (browser_name, scenario_id, corpus, event_type, corpus_type, leak, violation) VALUES (?, ?, ?, ?, ?, ?, ?) ";
if($browser_name!=null){ 
    $conn = new mysqli($servername, $username, $password, $dbname);
    if ($conn->connect_error) {
                $db_connection_status = "Fail:" . $conn->connect_error;
            } else {
                $db_connection_status = "success!";
                
                $stmt = $conn->prepare($sql);
                
                if ($stmt) {
                    $stmt->bind_param("sssssss", $browser_name, $scenario_id, $corpus, $event_type, $corpus_type, $leak_data, $violation);
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

    <h2>HSTS</h2>

</body>
</html>