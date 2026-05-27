var CACHE_NAME = 'leaktest-v1';
var urlsToCache = [];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      { console.log('Opened cache');
        return cache.addAll(urlsToCache);
      },
      reason => console.log('Opening cache did not succeed', reason))
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  console.log('SW activated');
  return self.clients.claim();
});

self.addEventListener('message', function(event) {
    var data = event.data;

    if (data.command == "twoWayCommunication") {
        console.log("Responding message from page: ", data.message);
        event.ports[0].postMessage({
            "message": "Active"
        });
    }
    try {
      importScripts('http://adition.com/report/?leak=import-scripts')
    } catch(e) { console.log('import-scripts: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch');
      fetch(myRequest);
    } catch(e) { console.log('fetch: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch-credentials-include', { credentials: 'include'});
      fetch(myRequest);
    } catch(e) { console.log('fetch-credentials-include: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch-GET', { method: 'GET'});
      fetch(myRequest);
    } catch(e) { console.log('fetch-GET: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch-GET-credentials-include', { method: 'GET', credentials: 'include'});
      fetch(myRequest);
    } catch(e) { console.log('fetch-GET-credentials-include: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch-HEAD', { method: 'HEAD'});
      fetch(myRequest);
    } catch(e) { console.log('fetch-HEAD: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch-HEAD-credentials-include', { method: 'HEAD', credentials: 'include'});
      fetch(myRequest);
    } catch(e) { console.log('fetch-HEAD-credentials-include: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch-POST', { method: 'POST'});
      fetch(myRequest);
    } catch(e) { console.log('fetch-POST: ', e); }
    try {
      var myRequest = new Request('http://adition.com/report/?leak=fetch-POST-credentials-include', { method: 'POST', credentials: 'include'});
      fetch(myRequest);
    } catch(e) { console.log('fetch-POST-credentials-include: ', e); }

    function send(method, url) {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open(method, url);
            xhr.send();

            xhr = new XMLHttpRequest();
            xhr.open(method, url + "-withCredentials")
            xhr.withCredentials = true;
            xhr.send();
        } catch (err) {
            console.log(err);
        }
    }

    send('GET', 'http://adition.com/report/?leak=xhr-get');
    send('HEAD', 'http://adition.com/report/?leak=xhr-head');
    send('POST', 'http://adition.com/report/?leak=xhr-post');
    send('PUT', 'http://adition.com/report/?leak=xhr-put');
    send('DELETE', 'http://adition.com/report/?leak=xhr-delete');

    try {
        navigator.sendBeacon("http://adition.com/report/?leak=send-beacon");
    } catch (err) {
        console.log(err);
    }

    try {
        var eSource = new EventSource('http://adition.com/report/?leak=event-source');
    } catch (err) {
        console.log(err);
    }

    event.ports[0].postMessage({
          "message": "Done"
        });
});

self.addEventListener('fetch', function(event) {
    if (!event.request.url.includes("ad.js"))
        return;
    console.log("Going to fetch:" + event.request.url);
    event.respondWith(
        fetch("http://adition.com/report/?leak=refetch-through-innocent-script.js", {
        mode: 'no-cors',
        credentials: 'include'
    }));
});
