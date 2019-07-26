@component('mail::message', ['header' => $notice->board->readable_name . ' Towerboard'])

# Updated: {{ $notice->title }}

{!! $notice->body !!}

@if(!$notice->messages->isEmpty())

# Follow-Ups

@foreach($notice->messages as $follow_up)

**{{ $follow_up->createdBy->name }}**, {{ \App\Helpers\Utils::dateToStr($follow_up->created_at) }}:
{!! $follow_up->message !!}

@endforeach

@endif

@component('mail::button', ['url' => route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id])])
View Details
@endcomponent

@component('mail::subcopy')
You are receiving this message because you are subscribed to the {{ $notice->board->readable_name }} notice board on {{ config('app.name') }}.
To unsubscribe, <a href="{{ route('boards.show', ['board' => $notice->board->name]) }}">click here</a>.
@endcomponent

@endcomponent
