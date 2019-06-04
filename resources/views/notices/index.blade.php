@extends('layouts.app', ['title' => 'My Notices'])

@section('content')

    <h2>My Notices</h2>

    @if(!$notices->isEmpty())

        @foreach ($notices as $key => $noticeGroup)
            <h3>{{ (new \Carbon\Carbon($key))->format('l jS F Y') }}</h3>
            <ul>
                @foreach ($noticeGroup as $notice)
                    <li>
                        {{ $notice->board->name }}:
                        <a href="{{ route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id]) }}">{{ $notice->title }}</a>
                    </li>
                @endforeach
            </ul>
        @endforeach
    @else
        <p>There are no notices on this board.</p>
    @endif

@endsection
