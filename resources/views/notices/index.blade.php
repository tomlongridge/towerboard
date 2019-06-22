@extends('layouts.app', ['title' => 'My Notices'])

@section('content')

<div class="row">

  @foreach ($boards as $board)
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-primary shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                          <a href="{{ route('boards.show', ['board' => $board->name]) }}">{{ $board->name }}</a>
                        </div>
                    </div>
                    <div class="col-auto">
                        @include('macros.boardicon', ['board' => $board])
                    </div>
                </div>
            </div>
        </div>
    </div>
  @endforeach

  @if(!$notices->isEmpty())
    @include('macros.noticelist', ['notices' => $notices, 'hideBoardName' => true])
  @else
    <p>There are no notices on this board.</p>
  @endif

@endsection
