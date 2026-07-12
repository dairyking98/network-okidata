const express = require('express');
const net = require('net');
const app = express();
const port = 3000;

// Parse raw binary data for requests with Content-Type "application/octet-stream"
app.use(express.raw({ type: 'application/octet-stream', limit: '1mb' }));

app.post('/send', (req, res) => {
  // Extract printer IP and port from query parameters.
  const printerIp = req.query.ip;
  const printerPort = req.query.port;
  // req.body is a Buffer containing the binary data.
  const data = req.body;
  
  console.log('Received binary data:', data);
  console.log('Printer IP:', printerIp, 'Port:', printerPort);
  
  // Create a TCP connection to the printer.
  const client = new net.Socket();
  client.connect(printerPort, printerIp, () => {
    console.log('Connected to printer.');
    // Send the binary data to the printer.
    client.write(data, () => {
      console.log('Data sent to printer.');
      client.end(); // Close the connection after sending.
    });
  });
  
  client.on('error', (err) => {
    console.error('Printer connection error:', err);
    res.status(500).send('Error sending data to printer: ' + err.message);
  });
  
  client.on('close', () => {
    console.log('Printer connection closed.');
    res.send('Data sent to printer successfully.');
  });
});

app.listen(port, () => {
  console.log(`Server listening at http://localhost:${port}`);
});
