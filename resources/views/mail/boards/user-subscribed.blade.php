@component('mail::message', ['header' => $board->readable_name . ' Towerboard'])

# {{ $board->readable_name }} Subscribed

You have been added to {{ $board->readable_name }} board by {{ $addedBy->name }}.

{{  config('app.name') }} is a virtual notice board for bell ringers - helping towers and ringing groups communicate with their members
and the wider ringing community.

@component('mail::subcopy')
If you wish to stop receiving these emails, <a href="{{ route('boards.show', ['board' => $board->name]) }}">click here</a> to unsubscribe.
@endcomponent

@endcomponent
