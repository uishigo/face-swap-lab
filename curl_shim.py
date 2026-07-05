#!/usr/bin/env python3
"""Drop-in replacement for curl.exe used by facefusion.download on this machine,
where the real curl.exe hangs on outbound HTTPS while Python's urllib works fine.
Implements only the subset of curl flags facefusion.curl_builder emits.
"""

import os
import sys
import time
import urllib.request
import urllib.error

def parse_args(argv):
	opts = {
		'user_agent': 'curl-shim/1.0',
		'connect_timeout': 30,
		'retry': 0,
		'output': None,
		'continue_at': None,
		'head': False,
		'create_dirs': False,
	}
	url = None
	i = 0
	while i < len(argv):
		arg = argv[i]
		if arg == '--user-agent':
			i += 1
			opts['user_agent'] = argv[i]
		elif arg == '--connect-timeout':
			i += 1
			opts['connect_timeout'] = float(argv[i])
		elif arg == '--retry':
			i += 1
			opts['retry'] = int(argv[i])
		elif arg == '--output':
			i += 1
			opts['output'] = argv[i]
		elif arg == '--continue-at':
			i += 1
			opts['continue_at'] = argv[i]
		elif arg == '-I':
			opts['head'] = True
		elif arg == '--create-dirs':
			opts['create_dirs'] = True
		elif arg in ('--location', '--silent', '--ssl-no-revoke', '-v'):
			pass
		elif arg.startswith('-'):
			pass
		else:
			url = arg
		i += 1
	return opts, url


def do_head(url, opts):
	request = urllib.request.Request(url, method = 'HEAD', headers = { 'User-Agent': opts['user_agent'] })
	try:
		with urllib.request.urlopen(request, timeout = opts['connect_timeout']) as response:
			sys.stdout.write('HTTP/1.1 ' + str(response.status) + os.linesep)
			for key, value in response.headers.items():
				sys.stdout.write(key + ': ' + value + os.linesep)
	except urllib.error.HTTPError as error:
		sys.stdout.write('HTTP/1.1 ' + str(error.code) + os.linesep)
		for key, value in error.headers.items():
			sys.stdout.write(key + ': ' + value + os.linesep)


def do_download(url, opts):
	output_path = opts['output']

	if opts['create_dirs']:
		directory = os.path.dirname(output_path)
		if directory:
			os.makedirs(directory, exist_ok = True)

	resume_from = 0
	if opts['continue_at'] == '-' and os.path.isfile(output_path):
		resume_from = os.path.getsize(output_path)

	headers = { 'User-Agent': opts['user_agent'] }
	if resume_from:
		headers['Range'] = 'bytes=' + str(resume_from) + '-'

	attempts = max(1, opts['retry'] + 1)
	last_error = None

	for attempt in range(attempts):
		try:
			request = urllib.request.Request(url, headers = headers)
			with urllib.request.urlopen(request, timeout = opts['connect_timeout']) as response:
				mode = 'ab' if resume_from and response.status == 206 else 'wb'
				if mode == 'wb':
					resume_from = 0
				with open(output_path, mode) as output_file:
					while True:
						chunk = response.read(1024 * 256)
						if not chunk:
							break
						output_file.write(chunk)
			return
		except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
			last_error = error
			time.sleep(1)

	if last_error:
		sys.stderr.write(str(last_error) + os.linesep)
		sys.exit(1)


def main():
	opts, url = parse_args(sys.argv[1:])

	if not url:
		sys.exit(1)

	if opts['head']:
		do_head(url, opts)
	else:
		do_download(url, opts)


if __name__ == '__main__':
	main()
