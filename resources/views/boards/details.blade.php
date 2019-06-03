@extends('boards.layout')

@section('subcontent')

    @if($board->tower)
        <p>@include('macros.tower', ['tower' => $board->tower])</p>
    @endif


    @if($board->website_url)
        <p><a href="{{ $board->website_url }}">Go to website&hellip;</a></p>
    @endif


    @if(!$board->affiliatedTo()->get()->isEmpty())
        <h2>Affiliated To</h2>
        <p>
            <ul>
            @foreach($board->affiliatedTo()->get() as $affiliate)
                <li><a href="{{ route('boards.show', ['board' => $affiliate->id]) }}">{{ $affiliate->name }}</a></li>
            @endforeach
            </ul>
        </p>
    @endif
    <p>
        This board is managed by: {{ $board->owner->name }}.
    </p>

    @can('update', $board)
        <a class="btn btn-primary" href="{{ route('boards.edit',[ 'board' => $board->id ]) }}">Edit</a>

        <form method="POST" action="{{ route('boards.destroy', [ 'board' => $board->id ]) }}" style="display: inline">
            @method("DELETE")
            @csrf
            <input type="submit" class="btn btn-primary" value="Delete" />
        </form>
    @endcan

    @if(!$board->affiliates()->get()->isEmpty())
        <h2>Affiliated Boards</h2>
        <p>
            Affiliates:
            <ul>
            @foreach($board->affiliates()->get() as $affiliate)
                <li><a href="{{ route('boards.show', ['board' => $affiliate->id]) }}">{{ $affiliate->name }}</a></li>
            @endforeach
            </ul>
        </p>
    @endif

@endsection
