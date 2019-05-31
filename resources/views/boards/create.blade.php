@extends('layouts.app')

@section('content')

    <h1 class="mt-4">Create Board</h1>

    <div class="container">
        <form method="POST" action="/boards">
            @csrf

            <div class="row">
                <label for="name">Name</label>
                <input type="text" class="form-control" id="name" name="name" placeholder="My Tower" value="" />
            </div>
            <div class="row">
                <label for="name">Tower</label>
                <select id="tower" name="tower_id" class="tb-dropdown"></select>
            </div>
            <div class="row">
                <label for="name">Guild</label>
                <select id="guild" name="guild_id" class="tb-dropdown"></select>
            </div>
            <div class="row">
                <input type="submit" class="btn btn-primary" id="menu-toggle" value="Create" />
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
            labelField: 'namehtml',
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
                    return '<div><span class="tb-dropdown-option">' + item.namehtml + '</span></div>';
                },
                item: function(item, escape) {
                    return '<div><span class="tb-dropdown-item">' + item.namehtml + '</span></div>';
                }
            }
        });

        $('#guild').selectize({
            preload: true,
            valueField: 'id',
            labelField: 'name',
            searchField: ['name'],
            sortField: ['name'],
            create: false,
            placeholder: 'Select/Type guild name',
            selectOnTab: true,
            load: function(query, callback) {
                $.ajax({
                    url: "{{ route('guilds.index') }}",
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
