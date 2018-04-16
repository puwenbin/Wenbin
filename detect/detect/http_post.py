#!/usr/bin/python
# coding: UTF-8

import urlparse  
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer



class GetHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		parsed_path = urlparse.urlparse(self.path)
		message_parts = [
				"CLIENT_VALUES:",
				"client_address=%s (%s)" % (self.client_address, self.address_string()),
				"command=%s" % self.command,
				"path=%s" % self.path,
				"real_path=%s" % parsed_path.path,
				"query=%s" % parsed_path.query,
				"request_version=%s" % self.request_version,
				"",
				"SERVER VALUES:",
				"server_version=%s" % self.server_version,
				"sys_version=%s" % self.sys_version,
				"protocol_version=%s" % self.protocol_version,
				"",
				"HEADERS RECEIVED:",
				]
		for name, value in sorted(self.headers.items()):
			message_parts.append("%s=%s" % (name, value.rstrip()))

		message_parts.append("")
		message = '\r\n'.join(message_parts)
		self.send_response(200)
		self.end_headers()
		self.wfile.write(message)
		return

if __name__ == "__main__":
	

	server = HTTPServer(("0.0.0.0", 80), GetHandler)
	print "Starting server, use <Ctrl-C> to stop"
	server.serve_forever()
