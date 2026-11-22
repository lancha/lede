// Execute against the real LuCI http.uc and lucihttp C extension, not a mock.
// baseline=true first proves the 100 KiB regression in the pinned original.
import { parse_message_body } from 'luci.http';

let maxfield = baseline ? 102400 : 1048576;
let count = 0;

function check(condition, message) {
	if (!condition)
		die(message);
}

function part(name, value, file) {
	return '--regression\r\nContent-Disposition: form-data; name="' + name + '"' +
		(file ? '; filename="synthetic.yaml"' : '') + '\r\n\r\n' + value + '\r\n';
}

function parse(body, ctype, cb, declared_length) {
	let msg = {
		env: {
			REQUEST_METHOD: 'POST',
			CONTENT_TYPE: ctype,
			CONTENT_LENGTH: declared_length ?? length(body)
		},
		params: {}
	};
	let offset = 0;
	parse_message_body(() => {
		if (offset >= length(body))
			return null;
		let chunk = substr(body, offset, 4096);
		offset += length(chunk);
		return chunk;
	}, msg, cb);
	return msg;
}

function run(name, callback, error_pattern) {
	let error;
	try { callback(); }
	catch (ex) { error = ex.message; }
	if (error_pattern)
		check(error && match(error, error_pattern), name + ': missing/unexpected error: ' + error);
	else
		check(!error, name + ': ' + error);
	count++;
	printf('PASS %s\n', name);
}

function multipart(fields, cb, declared_length) {
	return parse(fields + '--regression--\r\n', 'multipart/form-data; boundary=regression',
		cb, declared_length);
}

for (let size in [102399, 102400, 102401, 200555, 1048576, 1048577]) {
	run(sprintf('multipart ordinary field %d bytes', size), () => {
		let value = sprintf('%0' + size + 'd', 0);
		check(length(value) == size, 'incorrect synthetic fixture length');
		let msg = multipart(part('config', value));
		check(msg.params.config == value, 'field data changed');
	}, size > maxfield ? /maximum allow size/ : null);
}

run('two fields above old limit, duplicate names and CSRF token preserved', () => {
	let first = sprintf('%0200555d', 0), second = sprintf('%0200556d', 1);
	let msg = multipart(part('config', first) + part('config', second) + part('token', 'synthetic-token'));
	check(length(msg.params.config) == 2, 'duplicate fields lost');
	check(msg.params.config[0] == first && msg.params.config[1] == second, 'values changed');
	check(msg.params.token == 'synthetic-token', 'token field lost');
}, baseline ? /maximum allow size/ : null);

run('2 MiB file remains streaming', () => {
	let bytes = 0, calls = 0, eof = false;
	let msg = multipart(part('upload', sprintf('%02097152d', 0), true), (field, chunk, done) => {
		check(field.file == 'synthetic.yaml', 'filename lost');
		bytes += length(chunk);
		calls++;
		eof = done;
	});
	check(bytes == 2 * 1048576 && calls > 2 && eof, 'file not streamed completely');
	check(msg.params.upload.file == 'synthetic.yaml', 'file metadata lost');
});

run('Content-Length protection remains', () => {
	multipart(part('config', 'sample'), null, 1);
}, /exceeds Content-Length/);

run('URL-encoded 100 KiB remains accepted', () => {
	let value = sprintf('%0102400d', 0);
	check(parse('config=' + value, 'application/x-www-form-urlencoded').params.config == value,
		'URL-encoded value changed');
});
run('URL-encoded over 100 KiB remains rejected', () => {
	parse('config=' + sprintf('%0102401d', 0), 'application/x-www-form-urlencoded');
}, /maximum allow(ed)? size/);
run('raw 100 KiB remains accepted', () => {
	let value = sprintf('%0102400d', 0);
	check(parse(value, 'application/json').content == value, 'raw value changed');
});
run('raw over 100 KiB remains rejected', () => {
	parse(sprintf('%0102401d', 0), 'application/json');
}, /maximum allowed length/);

printf('%s: %d regression cases passed\n', baseline ? 'Original' : 'Patched', count);
