const dgram = require('dgram');
const http = require('http');
const socketIO = require('socket.io');
const axios = require('axios');
const FormData = require('form-data');

// ----------- CONFIG -----------
const UDP_PORT = 5005;
const HTTP_PORT = 80;

const MAILGUN_DOMAIN = '';
const MAILGUN_API_KEY = '';
const TO_EMAIL = 'christina.nguyen8712@gmail.com';

let latestRadarData = null;
// ------------------------------

// ----------- EMAIL FUNCTION -----------
function sendEmail(data) {
  const form = new FormData();
  form.append('from', `Mini AWACS <mailgun@${MAILGUN_DOMAIN}>`);
  form.append('to', TO_EMAIL);
  form.append('subject', 'Radar and Elevation Mechanism Data Update');
  form.append('text', `Radar Snapshot @ ${new Date().toLocaleString()}:\n\n${data}`);

  axios.post(`https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages`, form, {
    auth: {
      username: 'api',
      password: MAILGUN_API_KEY,
    },
    headers: form.getHeaders()
  }).then(response => {
    console.log('Email sent:', response.data);
  }).catch(error => {
    console.error('Email send error:', error.message);
  });
}
// --------------------------------------
// ----------- CREATE HTTP + WEBSOCKET SERVER -----------
const httpServer = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>Radar Live Feed</title>
        <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
      </head>
      <body>
        <h1>Radar Server is Running</h1>
        <p>Open DevTools → Console to see radar data</p>

        <script>
          const socket = io();
          socket.on('radarData', (data) => {
            console.log("📡 Radar Data:", data);
          });
        </script>
      </body>
    </html>
  `);
});

const io = socketIO(httpServer, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});
// ------------------------------------------------------
// ----------- SOCKET.IO CONNECTION -----------
io.on('connection', (socket) => {
  console.log("✅ WebSocket client connected");
});
// --------------------------------------------

// ----------- EMAIL TIMER (EVERY 5 MINUTES) -----------
setInterval(() => {
  if (latestRadarData) {
    sendEmail(latestRadarData);
  } else {
    console.log("⚠️ Timer triggered: No radar data yet.");
  }
}, 5 * 60 * 1000); // every 5 minutes
// ------------------------------------------------------

// ----------- UDP SERVER FOR RADAR DATA -----------
const udpServer = dgram.createSocket('udp4');

udpServer.on('message', (msg, rinfo) => {
  try {
    const data = JSON.parse(msg.toString());
    latestRadarData = data;

    console.log("📡 Received radar data:", data);
    io.emit('radarData', data);

    sendEmail(data);
  } catch (err) {
    console.error("❌ Failed to parse radar data:", err.message);
  }
});
// --------------------------------------------------
// ----------- START SERVERS -----------
udpServer.bind(UDP_PORT, () => {
  console.log(`✅ UDP server listening on port ${UDP_PORT}`);
});

httpServer.listen(HTTP_PORT, '0.0.0.0', () => {
  console.log(`✅ WebSocket + HTTP server running at http://0.0.0.0:${HTTP_PORT}`);
});
// -------------------------------------
