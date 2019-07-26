@component('mail::message', ['header' => $notice->board->readable_name . ' Towerboard'])

# Reply to Notice: {{ $notice->title }}

> {{ $message }}

Sent From: {{ $sentFrom->name }} ({{ $sentFrom->email }})

@component('mail::button', ['url' => route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id])])
View Notice
@endcomponent

@component('mail::subcopy')
You are receiving this message because you are the designated recipient of replies to this notice on the {{ $notice->board->readable_name }}
notice board on {{ config('app.name') }}.
@endcomponent

@endcomponent
