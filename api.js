var http = require('http');
var querystring = require('querystring');

//process.argv.forEach(function (val, index, array) {
//  console.log(index + ': ' + val);
//});

var auth = process.argv[2] + ':';
var method = process.argv[3].toLowerCase();
var pathSeed = '/v2/treasurer/' + process.argv[4] + '.json';
var data = process.argv[5];
if (method == 'get'){
 var path = (process.argv[5])? pathSeed + '?' + data:pathSeed;
}
if (method == 'post'){
 var path = pathSeed;
}

var options = {
  host: 'api.kellpro.com',
  port: 80,
  path: path,
  method: method,
  auth: auth
};
function getData(){
    var req = http.request(options, function(res) {
    //  console.log('STATUS: ' + JSON.stringify(res.statusCode));
    //  console.log('HEADERS: ' + JSON.stringify(res.headers));
      res.setEncoding('utf8');
      res.on('data', function (chunk) {
        console.log(chunk);
      });
    });

    req.on('error', function(e) {
      console.log('problem with request: ' + e.message);
    });

    req.write(data + '\n');
    req.end();
}

function postData(data){
    var post_options = {
      host: 'api.kellpro.com',
      port: '80',
      path: path,
      method: method,
      auth: auth,
      headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Content-Length': data.length
      }
    };
    var req = http.request(post_options, function(res) {
        res.setEncoding('utf8');
        res.on('data', function (chunk) {
          console.log(chunk);
        });
    });

    req.write(data);
    req.end();
}

// write data to request body
if (method == 'get'){
    getData();
}

if (method == 'post'){
    postData(data);
}
