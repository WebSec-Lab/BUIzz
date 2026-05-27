// Array of permissions
var permissions = [
  "geolocation"
];

processPermissions();

// Iterate through the permissions and log the result
async function processPermissions() {
  let count = 1;
  let violation = 0;
  for (const permission of permissions) {
    let result = await getPermission(permission);
    if(result == true){
      violation = violation + count 
    }
  };

  console.log(violation);
  // sendBeacon survives page unload — fetch() loses reports when the scenario
  // navigates away (e.g. blob: tab closed immediately after open).
  navigator.sendBeacon(origin+"/report/report?query=" + String(violation));
}

// Query a single permission in a try...catch block and return result
async function getPermission(permission) {
  try {
    let result;
    if (permission === "top-level-storage-access") {
      result = await navigator.permissions.query({
        name: permission,
        requestedOrigin: window.location.origin,
      });
    } else {
      result = await navigator.permissions.query({ name: permission });
    }
    if (result.state == "denied"){
      return false;
    }else{
      return true;
    };
  } catch (error) {
    return false;
  }
}

