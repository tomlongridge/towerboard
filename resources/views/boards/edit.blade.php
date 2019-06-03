@extends('layouts.app', ['title' => isset($board) ? 'Edit Board' : 'Create Board'])

@section('content')

    <div class="container">
        @if(isset($board))
            <form method="POST" action="{{ route('boards.update', [ 'board' => $board->id ]) }}">
            @method('PATCH')
        @else
            <form method="POST" action="{{ route('boards.store') }}">
        @endif
            @csrf

            <div class="row">
                <label for="name">Name</label>
                <input type="text" class="form-control" id="name" name="name" placeholder="My Tower"
                       value="{{ isset($board) ? $board->name : '' }}" />
            </div>
            <div class="row">
                <label for="name">Tower</label>
                <select id="tower" name="tower_id" class="tb-dropdown"></select>
            </div>
            <div class="row">
                <label for="name">Website</label>
                <input type="text" class="form-control" id="website_url" name="website_url" placeholder="http://www.yoursite.com"
                       value="{{ isset($board) ? $board->website : '' }}" />
            </div>
            <div class="row">
                <input type="submit" class="btn btn-primary" id="menu-toggle" value="Save" />
            </div>
        </form>
    </div>

    @if(!$errors->isEmpty())
        <ul class="alert alert-danger">
        @foreach($errors->all() as $error)
            <li>{{ $error }}</li>
        @endforeach
        </ul>
    @endif

@endsection

@section('pagescripts')

<script>
        $('#tower').selectize({
            preload: true,
            valueField: 'id',
            labelField: 'name',
            searchField: ['name'],
            sortField: ['country', 'county', 'town', 'area'],
            create: false,
            placeholder: 'Select/Type tower name',
            selectOnTab: true,
            load: function(query, callback) {
                $.ajax({
                    url: "{{ route('towers.index') }}",
                    type: 'GET',
                    dataType: 'json',
                    error: function(e) {
                        callback();
                    },
                    success: function(res) {
                        callback(res);
                    }
                });
            },
            render: {
                option: function(item, escape) {
                    return '<div><span class="tb-dropdown-option">' + item.name + '</span></div>';
                },
                item: function(item, escape) {
                    return '<div><span class="tb-dropdown-item">' + item.name + '</span></div>';
                }
            }
        });

    </script>

@endsection
