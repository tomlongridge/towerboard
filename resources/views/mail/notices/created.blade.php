@component('mail::message', ['header' => $notice->board->readable_name . ' Towerboard'])

# {{ $notice->title }}

{!! $notice->body !!}

@component('mail::button', ['url' => route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id])])
View Details
@endcomponent

@component('mail::subcopy')
You are receiving this message because you are subscribed to the {{ $notice->board->readable_name }} board on {{ config('app.name') }}.
To unsubscribe, <a href="{{ route('boards.subscribe', ['board' => $notice->board]) }}">click here</a>.
@endcomponent

@endcomponent
