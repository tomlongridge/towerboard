@extends('layouts.app')

@section('content')

    <h1 class="mt-4">Account Details</h1>

    <div class="container">
        <form method="POST" action="{{ route('accounts.update') }}">
            @method('PATCH')
            @csrf

            <div class="row">
                <label for="forename">Forename</label>
                <input type="text" class="form-control" id="forename" name="forename" placeholder="Your Name" value="{{ $user->forename }}" />
            </div>
            <div class="row">
                <label for="middle_initials">Middle Initials</label>
                <input type="text" class="form-control" id="middle_initials" name="middle_initials" placeholder="Your Name" value="{{ $user->middle_initials }}" />
            </div>
            <div class="row">
                <label for="surname">Surname</label>
                <input type="text" class="form-control" id="surname" name="surname" placeholder="Your Name" value="{{ $user->surname }}" />
            </div>
            <div class="row">
                <label for="name">Email Address</label>
                <input type="text" class="form-control" id="email" name="email" placeholder="tom@example.com" value="{{ $user->email }}" />
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
