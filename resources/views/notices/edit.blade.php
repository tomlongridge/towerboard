@extends('layouts.app', ['title' => 'Edit Notice'])

@section('content')

  <div class="container">
    @isset($notice)
      <form method="POST" action="{{ route('notices.update', [ 'board' => $board->name, 'notice' => $notice->id ]) }}">
        @method('PATCH')
    @else
      <form method="POST" action="{{ route('notices.store', [ 'board' => $board->name ]) }}">
    @endisset
        @csrf

        <div class="row">
          <label for="title">Title</label>
          <input type="text" class="form-control" id="title" name="title" placeholder="Title" value="{{ old('title', isset($notice) ? $notice->title : '') }}" />
        </div>
        <div class="row">
          <label for="body">Body</label>
          <textarea class="form-control" id="body" name="body">
              {{ old('body', isset($notice) ? $notice->body : '') }}
          </textarea>
        </div>
        <div class="row">
          <label for="distribution">Send To</label>
          <select name="distribution" id="distribution" class="form-control">
            @foreach (\App\Enums\SubscriptionType::getInstances() as $type)
              <option value="{{ $type->value }}"
                {{ old('distribution', isset($notice) ? $notice->distribution : \App\Enums\SubscriptionType::getInstance(\App\Enums\SubscriptionType::BASIC))->key == $type ? 'selected' : '' }} >
                {{ ucwords(str_plural($type->description)) }}
              </option>
            @endforeach
          </select>
        </div>
        <div class="row">
          <input type="submit" class="btn btn-primary" id="menu-toggle" value="Save" />
          &nbsp;
          <a href="{{ url()->previous() }}" class="btn btn-secondary">Back</a>
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
