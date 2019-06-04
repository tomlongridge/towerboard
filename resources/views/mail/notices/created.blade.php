@component('mail::message')
# {{ $notice->board->name }} Notice Board
## {{ $notice->title }}

{{ $notice->body }}

@component('mail::button', ['url' => route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id])])
View Details
@endcomponent

@component('mail::subcopy')
You are receiving this message because you are subscribed to the {{ $notice->board->name }} notice board on {{ config('app.name') }}.
To unsubscribe, <a href="{{ route('boards.show', ['board' => $notice->board->name]) }}">click here</a>.
@endcomponent

@endcomponent
