@component('mail::message', ['header' => $board->readable_name . ' Towerboard'])

# {{ $board->readable_name }} Subscription

You have requested to {{ $subscribe ? 'subscribe to' : 'unsubscribe from' }} the {{ $board->readable_name }} notice board.

If you wish to do so, please click the following link:

@component('mail::button', ['url' => $link, 'color' => 'primary'])
{{ $subscribe ? 'Subscribe' : 'Unsubscribe' }}
@endcomponent

Alternatively paste the following into your browser:

<a href="{{ $link }}">{{ $link }}</a>

@endcomponent
