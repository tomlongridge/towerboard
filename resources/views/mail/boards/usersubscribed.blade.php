@component('mail::message')
# {{ $board->readable_name }}

You have been added to {{ $board->readable_name }} notice board by {{ $addedBy->name }}.

Towerboard is a online version of your tower notice board - helping towers communicate with their members
and the wider ringing community.

@component('mail::subcopy')
If you wish to stop receiving these emails, <a href="{{ route('boards.show', ['board' => $board->name]) }}">click here</a> to unsubscribe.
@endcomponent

@endcomponent
