@extends('boards.layout')

@section('subcontent')

    @if($board->tower)
        <p>@include('macros.tower', ['tower' => $board->tower])</p>
    @endif


    @if($board->website_url)
        <p><a href="{{ $board->website_url }}">Go to website&hellip;</a></p>
    @endif


    @if(!$board->affiliatedTo->isEmpty())
        <h2>Affiliated To</h2>
        <p>
            <ul>
            @foreach($board->affiliatedTo as $affiliate)
                <li><a href="{{ route('boards.show', ['board' => $affiliate->name]) }}">{{ $affiliate->name }}</a></li>
            @endforeach
            </ul>
        </p>
    @endif
    <p>
        This board is managed by: {{ $board->owner->name }}.
    </p>

    @can('update', $board)
        <a class="btn btn-primary" href="{{ route('boards.edit', ['board' => $board->name]) }}">Edit</a>

        <form method="POST" action="{{ route('boards.destroy', ['board' => $board->name]) }}" style="display: inline">
            @method("DELETE")
            @csrf
            <input type="submit" class="btn btn-primary" value="Delete" />
        </form>
    @endcan

    @if(!$board->affiliates->isEmpty())
        <h2>Affiliated Boards</h2>
        <p>
            Affiliates:
            <ul>
            @foreach($board->affiliates as $affiliate)
                <li><a href="{{ route('boards.show', ['board' => $affiliate->name]) }}">{{ $affiliate->name }}</a></li>
            @endforeach
            </ul>
        </p>
    @endif

@endsection
