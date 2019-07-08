@component('mail::message')
# {{ $board->readable_name }}

You have requested to unsubscribe from the {{ $board->readable_name }} notice board.

If you wish to do so, please click the following link:

@component('mail::button', ['url' => $unsubscribeLink, 'color' => 'primary'])
Unsubscribe
@endcomponent

Alternatively paste the following into your browser:

<a href="{{ $unsubscribeLink }}">{{ $unsubscribeLink }}</a>

@endcomponent
