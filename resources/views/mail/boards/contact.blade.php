@component('mail::message', ['header' => $board->readable_name . ' Towerboard'])

# Message from Contact Form

The following message was sent on {{ \App\Helpers\Utils::dateToStr($sentAt) }} by {{ $sentFrom->name }} ({{ $sentFrom->email }}) using the contact form
on the {{ $board->readable_name }} board:

> {{ $messageBody }}

@component('mail::subcopy')
You are receiving this message because you are on the contact list of the {{ $board->readable_name }} notice board on {{ config('app.name') }}.
@endcomponent

@endcomponent
