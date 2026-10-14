<?php
declare(strict_types=1);

$forwardedProto = strtolower((string)($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? ''));
$isSecure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || $forwardedProto === 'https';
session_set_cookie_params([
    'lifetime' => 0,
    'path' => '/',
    'secure' => $isSecure,
    'httponly' => true,
    'samesite' => 'Lax',
]);
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

$templatePath = __DIR__ . '/index.html';
$template = is_file($templatePath) ? file_get_contents($templatePath) : false;
if ($template === false) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'The page template is unavailable.';
    exit;
}

header('Content-Type: text/html; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: private, no-store, max-age=0');
$token = htmlspecialchars((string)$_SESSION['csrf_token'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$started = (string)time();
echo str_replace(
    ['%%CSRF_TOKEN%%', '%%FORM_STARTED_AT%%'],
    [$token, $started],
    $template
);
