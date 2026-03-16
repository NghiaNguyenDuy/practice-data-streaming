const BUFFER_SIZE = 5;
// var INGESTION_ENDPOINT = 'http://localhost:8080/dataingestion/ingest/cities';
// uncomment this for the fallback example
var INGESTION_ENDPOINT = 'http://localhost:8080/dataingestionfallback/ingest/cities';

$(document).ready(function(){

   function send_clicks(clicks) {
     var to_retry = JSON.parse(localStorage.getItem('clicks_to_retry')) ?? [];
     var to_send = to_retry
     function create_payload(click) {
       to_send.push(JSON.stringify(click))
     }
     clicks.forEach(create_payload);
   
     $.ajax({ 
        async: false,
        crossDomain: true,
        contentType: 'application/json',
        url: INGESTION_ENDPOINT+'/user1',
        data: JSON.stringify(to_send),
        type: 'post',
        success: function(result) {
          console.log("OK!")
          if (!result.success) {
            console.log("An error occured while sending records...");
            clicks_to_retry = [];
            function add_retry(click) {
              clicks_to_retry.push(click);
            }
            result.failed.forEach(add_retry);
            localStorage.setItem('clicks_to_retry', JSON.stringify(clicks_to_retry));
          } else {
            localStorage.removeItem('clicks_to_retry');
          }
          localStorage.removeItem('clicks');
        },
        error: function(jqXHR, textStatus, errorThrown) {
	  console.log(textStatus);
	  console.log(errorThrown);
        }
     });
   }
  
   const click = {"link": window.location.href, 'time': Date.now(), 'id': crypto.randomUUID()};
   var clicks = JSON.parse(localStorage.getItem('clicks')) ?? [];
   clicks.push(click);
   localStorage.setItem('clicks', JSON.stringify(clicks));
   
   const undelivered_clicks_to_retry = JSON.parse(localStorage.getItem('clicks_to_retry')) ?? [];
   if (clicks.length >= BUFFER_SIZE || undelivered_clicks_to_retry.length > 0) {
      console.log("Pushing clicks to the endpoint")
      send_clicks(clicks);
   }
}); 
