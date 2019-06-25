@extends('layouts.app', ['title' => isset($board) ? 'Edit Board' : 'Create Board', 'activeBoard' => (isset($board) ? $board : null)])

@section('content')

  <div class="card shadow mb-4">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">
        {{ isset($board) ? 'Edit' : 'Create New' }} Board
      </h6>
    </div>
    <div class="card-body px-5">

      @isset($board)
        <form method="POST" id="edit-form" action="{{ route('boards.update', ['board' => $board->name]) }}" novalidate>
          @method('PATCH')
      @else
        <form method="POST" id="edit-form" action="{{ route('boards.store') }}" novalidate>
      @endif
        @csrf

        <div class="form-group">
          <div class="row">
            <div class="col">
              Board Type
              <small>(What kind of organisation does your board represent?)</small>
            </div>
          </div>
          <div class="row px-1 pt-2">
            <span class="text-nowrap px-2">
              <input type="radio" name="type" id="type-tower" value="{{ \App\Enums\BoardType::TOWER }}"
                    {{ old('type', isset($board) ? $board->type : \App\Enums\BoardType::TOWER) == \App\Enums\BoardType::TOWER ? 'checked' : ''}} />
              <label for="type-tower">Tower</label>
            </span>
            <span class="text-nowrap px-2">
              <input type="radio" name="type" id="type-branch" value="{{ \App\Enums\BoardType::BRANCH }}"
                    {{ old('type', isset($board) ? $board->type : \App\Enums\BoardType::TOWER) == \App\Enums\BoardType::BRANCH ? 'checked' : ''}} />
              <label for="type-branch">Branch/District</label>
            </span>
            <span class="text-nowrap px-2">
              <input type="radio" name="type" id="type-guild" value="{{ \App\Enums\BoardType::GUILD }}"
                    {{ old('type', isset($board) ? $board->type : \App\Enums\BoardType::TOWER) == \App\Enums\BoardType::GUILD ? 'checked' : ''}} />
              <label for="type-guild">Guild/Association</label>
            </span>
            <span class="text-nowrap px-2">
              <input type="radio" name="type" id="type-other" value=""
                    {{ old('type', isset($board) ? $board->type : \App\Enums\BoardType::TOWER) == '' ? 'checked' : ''}} />
              <label for="type-other">Other</label>
            </span>
          </div>
        </div>
        <div class="form-group">
            <label for="readable_name">Name</label>
            <input type="text" class="form-control {{ $errors->has('name') ? 'is-invalid' : '' }}" id="readable_name" name="readable_name" placeholder="My Tower"
            value="{{ old('readable_name', isset($board) ? $board->readable_name : '') }}" required/>
            <div class="invalid-feedback">@error('name') {{ $message }} @else Please enter the name of the board. @enderror</div>
            <small>(A short unique name for your board to be used for the page address.)</small>
        </div>
        <div class="form-group" id="tower-row"
        @if(!isset($board) || $board->type != \App\Enums\BoardType::TOWER)
             style="display:none"
        @endif
        >
            <label for="name">Tower</label>
            <select id="tower" name="tower_id" class="tb-dropdown">
                @isset($board)
                    <option value="{{ $board->tower_id }}" selected="selected">
                        @include('macros.tower', ['tower' => $board->tower])
                    </option>
                @endisset
            </select>
        </div>
        <div class="form-group">
          <label for="website_url">Website</label>
          <input type="text" class="form-control {{ $errors->has('website_url') ? 'is-invalid' : '' }}" id="website_url" name="website_url"
                 placeholder="http://www.yoursite.com" value="{{ old('website_url', isset($board) ? $board->website_url : '') }}" />
          <div class="invalid-feedback">@error('website_url') {{ $message }} @enderror</div>
        </div>
        <div class="form-group">
          <label for="address">Postal Address</label>
          <input type="text" class="form-control" id="address" name="address" placeholder="Church Lane"
                  value="{{ old('address', isset($board) ? $board->address : '') }}" />
        </div>
        <div class="form-group">
          <label for="postcode">Postcode</label>
          <input type="text" class="form-control" id="postcode" name="postcode" placeholder="AB1 2YZ"
                  value="{{ old('postcode', isset($board) ? $board->postcode : '') }}" />
        </div>
        <div class="form-group">
          <span class="control-label">Location</span>
          <div class="col">
            <div class="form-group row pt-2">
              <label for="latitude">Lat:</label>
              <div class="col-md-2">
                <input type="number" min="-90" max="90" step="any" id="latitude" name="latitude" placeholder=""
                        class="form-control {{ $errors->has('latitude') ? 'is-invalid' : '' }}"
                        value="{{ old('latitude', isset($board) ? $board->latitude : '') }}" />
                <div class="invalid-feedback">@error('latitude') {{ $message }} @else Invalid latitude - must be between -90 and 90 @enderror</div>
              </div>
              <label for="longitude">Lon:</label>
              <div class="col-md-2">
                <input type="number" min="-180" max="180" step="any" id="longitude" name="longitude" placeholder=""
                        class="form-control {{ $errors->has('longitude') ? 'is-invalid' : '' }}"
                        value="{{ old('longitude', isset($board) ? $board->longitude : '') }}" />
                <div class="invalid-feedback">@error('longitude') {{ $message }} @else Invalid longitude - must be between -90 and 90 @enderror</div>
              </div>
            </div>
          </div>
        </div>
        <div class="form-group">
          <label for="can_post">Who Can Post?</label>
          <select name="can_post" id="can_post" class="form-control">
            @foreach (\App\Enums\SubscriptionType::getInstances() as $type)
              @if($type->value > \App\Enums\SubscriptionType::BASIC)
              <option value="{{ $type->value }}"
                {{ old('can_post', isset($board) ? $board->can_post : \App\Enums\SubscriptionType::getInstance(\App\Enums\SubscriptionType::BASIC)) == $type ? 'selected' : '' }} >
                {{ ucwords(str_plural($type->description)) }}
              </option>
              @endif
            @endforeach
          </select>
        </div>
        <div class="form-group">
          @isset($board)
            <a href="{{ route('boards.details', ['board' => $board]) }}" class="btn btn-secondary btn-icon-split">
          @else
            <a href="{{ route('boards.index') }}" class="btn btn-secondary btn-icon-split">
          @endisset
            <span class="icon text-white-50"><i class="fas fa-arrow-left"></i></span>
            <span class="text">Back</span>
          </a>
          <button type="submit" class="btn btn-success btn-icon-split">
            <span class="icon text-white-50"><i class="fas fa-check"></i></span>
            <span class="text">Save</span>
          </button>
        </div>
      </form>
    </div>
  </div>

@endsection

@section('pagescripts')
<script>
  $('input[name=type]:radio').on('change', function(event) {
    if (event.target.value == {{ \App\Enums\BoardType::TOWER }}) {
      $('#tower-row').show(250);
    } else {
      $('#tower-row').hide(250);
    }
  });

  $('#edit-form').on('submit', function(event) {
    if (this.checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.classList.add('was-validated');
  });

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
    },
  });
</script>

@endsection
