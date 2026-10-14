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
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store, max-age=0');

$wantsJson = str_contains(strtolower((string)($_SERVER['HTTP_ACCEPT'] ?? '')), 'application/json');

function respond(int $status, bool $ok, string $message): never
{
    global $wantsJson;
    http_response_code($status);
    if ($wantsJson) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['ok' => $ok, 'message' => $message], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        exit;
    }
    $code = $ok ? 'sent' : 'failed';
    header('Location: index.php?enquiry=' . $code . '#enquiry', true, 303);
    exit;
}

function cleanLine(string $value): string
{
    $value = strip_tags($value);
    $value = preg_replace('/[\r\n\x00-\x1F\x7F]+/u', ' ', $value) ?? '';
    return trim(preg_replace('/\s+/u', ' ', $value) ?? '');
}

function cleanMultiline(string $value): string
{
    $value = strip_tags($value);
    $value = str_replace(["\r\n", "\r"], "\n", $value);
    $value = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $value) ?? '';
    return trim($value);
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    respond(405, false, 'Please send the enquiry using the form.');
}
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 12000) {
    respond(413, false, 'The submitted form is too large. Please shorten your message and try again.');
}

$submittedToken = (string)($_POST['csrf_token'] ?? '');
$sessionToken = (string)($_SESSION['csrf_token'] ?? '');
if ($sessionToken === '' || $submittedToken === '' || !hash_equals($sessionToken, $submittedToken)) {
    respond(403, false, 'This form has expired. Please refresh the page and try again.');
}

$project = (string)($_POST['project'] ?? '');
if (!in_array($project, ['asset-cleaning', 'logo-redesign'], true)) {
    respond(400, false, 'The form could not be identified. Please refresh the page and try again.');
}

// A filled honeypot is treated as a successful submission but is never emailed.
if (trim((string)($_POST['website'] ?? '')) !== '') {
    respond(200, true, 'Thank you.');
}

$startedAt = filter_var((string)($_POST['form_started_at'] ?? ''), FILTER_VALIDATE_INT);
if ($startedAt === false || time() - (int)$startedAt < 2 || time() - (int)$startedAt > 86400) {
    respond(422, false, 'Please refresh the page and complete the form again.');
}
if (isset($_SESSION['last_submission']) && time() - (int)$_SESSION['last_submission'] < 45) {
    respond(429, false, 'Please wait a moment before sending another enquiry.');
}

$name = cleanLine((string)($_POST['name'] ?? ''));
$company = cleanLine((string)($_POST['company'] ?? ''));
$email = trim((string)($_POST['email'] ?? ''));
$email = str_replace(["\r", "\n", "\0"], '', $email);
$telephone = cleanLine((string)($_POST['telephone'] ?? ''));
$details = cleanMultiline((string)($_POST[$project === 'asset-cleaning' ? 'sites' : 'message'] ?? ''));

if ($name === '' || strlen($name) > 480 || !filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 254) {
    respond(422, false, 'Please provide a valid name and email address.');
}
if ($project === 'asset-cleaning' && $details === '') {
    respond(422, false, 'Please tell us about the sites or work involved.');
}
if ($project === 'logo-redesign' && $details === '') {
    respond(422, false, 'Please add a short message.');
}
if (strlen($company) > 720 || strlen($telephone) > 320 || strlen($details) > 20000) {
    respond(422, false, 'One or more fields are too long. Please shorten the details and try again.');
}

$recipient = getenv('BIONIC_CONTACT_EMAIL') ?: 'info@thebioniceye.co.uk';
$from = getenv('BIONIC_MAIL_FROM') ?: 'no-reply@thebioniceye.co.uk';
if (!filter_var($recipient, FILTER_VALIDATE_EMAIL) || !filter_var($from, FILTER_VALIDATE_EMAIL)) {
    respond(503, false, 'The enquiry service is not configured. Please email info@thebioniceye.co.uk.');
}

$subject = $project === 'asset-cleaning'
    ? 'Asset cleaning enquiry — The Bionic Eye'
    : 'Logo identity proposal enquiry — The Bionic Eye';
$body = implode("\n", [
    'Website enquiry: ' . ($project === 'asset-cleaning' ? 'Asset Cleaning' : 'Logo identity proposal'),
    'Name: ' . $name,
    'Company: ' . ($company !== '' ? $company : 'Not provided'),
    'Email: ' . $email,
    'Telephone: ' . ($telephone !== '' ? $telephone : 'Not provided'),
    $project === 'asset-cleaning' ? 'Sites or work involved:' : 'Message:',
    $details,
]);
$headers = [
    'From: The Bionic Eye Website <' . $from . '>',
    'Reply-To: ' . $email,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'X-Mailer: PHP/' . PHP_VERSION,
];
$encodedSubject = '=?UTF-8?B?' . base64_encode($subject) . '?=';

if (!function_exists('mail') || !@mail($recipient, $encodedSubject, $body, implode("\r\n", $headers))) {
    respond(503, false, 'We could not send your enquiry just now. Please email info@thebioniceye.co.uk.');
}

$_SESSION['last_submission'] = time();
respond(200, true, 'Thank you. Your enquiry has been sent.');
