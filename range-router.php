<?php
require_once __DIR__ . '/video_range.php';
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/');
if (preg_match('~^/assets/videos/.+\.mp4$~i', $path)) {
    $assetRoot = realpath(__DIR__ . '/assets/videos');
    $file = realpath(__DIR__ . $path);
    if ($assetRoot !== false && $file !== false && str_starts_with($file, $assetRoot . DIRECTORY_SEPARATOR)) {
        bionic_stream_video_range($file);
    }
}
return false;
