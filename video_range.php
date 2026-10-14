<?php
/** Stream an MP4 file with single-byte-range support for PHP's built-in preview server. */
function bionic_stream_video_range(string $file): void
{
    if (!is_file($file) || !is_readable($file)) { http_response_code(404); exit; }
    $size = filesize($file); $start = 0; $end = max(0, $size - 1); $range = $_SERVER['HTTP_RANGE'] ?? '';
    if ($range !== '') {
        if (!preg_match('/^bytes=(\d*)-(\d*)$/', trim($range), $m) || ($m[1] === '' && $m[2] === '')) { http_response_code(416); header("Content-Range: bytes */$size"); exit; }
        if ($m[1] === '') { $suffix=(int)$m[2]; if ($suffix<=0) { http_response_code(416); header("Content-Range: bytes */$size"); exit; } $start=max(0,$size-$suffix); }
        else { $start=(int)$m[1]; }
        $end=$m[2] === '' ? $size-1 : min((int)$m[2],$size-1);
        if ($start>$end || $start>=$size) { http_response_code(416); header("Content-Range: bytes */$size"); exit; }
        http_response_code(206); header("Content-Range: bytes $start-$end/$size");
    }
    $length=$end-$start+1; header('Content-Type: video/mp4'); header('Accept-Ranges: bytes'); header('Content-Length: '.$length); header('Cache-Control: public, max-age=3600'); header('X-Content-Type-Options: nosniff');
    if (($_SERVER['REQUEST_METHOD']??'GET')==='HEAD') exit;
    while(ob_get_level()>0) ob_end_clean(); @ini_set('zlib.output_compression','0'); $f=fopen($file,'rb'); if($f===false){http_response_code(500);exit;} fseek($f,$start); $left=$length;
    while($left>0&&!feof($f)&&!connection_aborted()){ $chunk=fread($f,min(1024*1024,$left)); if($chunk===false||$chunk==='')break; echo $chunk; $left-=strlen($chunk); flush(); }
    fclose($f); exit;
}
