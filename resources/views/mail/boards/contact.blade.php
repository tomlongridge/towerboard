@component('mail::message')
# {{ $board->readable_name }}
## Message from Contact Form

The following message was sent on {{ \App\Helpers\TowerBoardUtils::dateToStr($sentAt) }} by {{ $sentFrom->name }} ({{ $sentFrom->email }}) using the contact form
on the {{ $board->readable_name }} board:

> {{ $messageBody }}

@component('mail::subcopy')
You are receiving this message because you are an administrator of the {{ $board->readable_name }} notice board on {{ config('app.name') }}.
@endcomponent

@endcomponent
