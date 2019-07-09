@extends('layouts.app', ['title' => $activeBoard->readable_name, 'activeBoard' => $activeBoard])

@section('content')

  <div class="card border-bottom-primary shadow h-100 py-2 my-4">
    <div class="card-body">
      <div class="row no-gutters align-items-center">
        <div class="col mr-2">
          <div class="h5 mb-0 font-weight-bold text-gray-800">
            @include('macros.board', ['board' => $activeBoard])
          </div>
        </div>
        <div class="col-auto">
          @include('macros.board-icon', ['board' => $activeBoard])
        </div>
      </div>
    </div>
  </div>

  @yield('subcontent')

@endsection
