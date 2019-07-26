@component('mail::message')
# {{ $board->readable_name }} Board Created

Thank you for registering a board on {{ config('app.name') }}. In order to ensure all boards are geniune, it will only be
public on the website once it has been approved. We aim to do this as quickly as we can; you will receive an email to let
you know when it is complete. Until that time, you (and only you) can see the board on the website or using the link below.

@component('mail::button', ['url' => route('boards.show', ['board' => $board])])
View Board
@endcomponent

@endcomponent
