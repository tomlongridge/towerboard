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
        <div class="form-group" id="tower-row"
        @if(isset($board) && $board->type != \App\Enums\BoardType::TOWER)
             style="display:none"
        @endif
        >
            <label for="name">Tower</label>
            <select id="tower" name="tower_id">
                @isset($board)
                    <option value="{{ $board->tower_id }}" selected="selected">
                        @include('macros.tower', ['tower' => $board->tower])
                    </option>
                @endisset
            </select>
        </div>
        <div class="form-group">
            <label for="readable_name">Name</label>
            <input type="text" class="form-control {{ $errors->has('name') ? 'is-invalid' : '' }}" id="readable_name" name="readable_name" placeholder="My Tower"
                  value="{{ old('readable_name', isset($board) ? $board->readable_name : '') }}" required/>
            <div class="invalid-feedback">@error('name') {{ $message }} @else Please enter the name of the board. @enderror</div>
            <small>(A short unique name for your board to be used for the page address: <span id="board_url" style="font-weight: bold; color: blue; text-decoration: underline"></span>)</small>
        </div>
        <div class="form-group">
          <label for="website_url">Website</label>
          <input type="text" class="form-control {{ $errors->has('website_url') ? 'is-invalid' : '' }}" id="website_url" name="website_url"
                 placeholder="http://www.yoursite.com" pattern="https?://.+"
                 value="{{ old('website_url', isset($board) ? $board->website_url : '') }}" />
          <div class="invalid-feedback">@error('website_url') {{ $message }} @else The website address is not valid - it should start http:// or https:// @enderror</div>
        </div>
        <div class="form-group">
          <label for="website_url">Facebook</label>
          <div class="input-group mb-2 mr-sm-2">
            <div class="input-group-prepend">
              <div class="input-group-text">https://www.facebook.com/</div>
            </div>
            <input type="text" class="form-control {{ $errors->has('facebook_url') ? 'is-invalid' : '' }}" id="facebook_url" name="facebook_url"
                  placeholder="/groups/my-tower" pattern="[A-Za-z0-9\.\-\/]+"
                  value="{{ old('facebook_url', isset($board) ? $board->facebook_url : '') }}" />
            <div class="invalid-feedback">@error('facebook_url') {{ $message }} @else The Facebook address is not valid - just include the part after facebook.com/ @enderror</div>
          </div>
        </div>
        <div class="form-group">
          <label for="twitter_handle">Twitter</label>
          <div class="input-group mb-2 mr-sm-2">
            <div class="input-group-prepend">
              <div class="input-group-text">@</div>
            </div>
            <input type="text" class="form-control {{ $errors->has('twitter_handle') ? 'is-invalid' : '' }}" id="twitter_handle" name="twitter_handle"
                   placeholder="mytower" value="{{ old('twitter_handle', isset($board) ? $board->twitter_handle : '') }}"
                   pattern="[A-Za-z_]{1,15}" />
            <div class="invalid-feedback">@error('twitter_handle') {{ $message }} @else The Twitter handle should be only characters or underscores @enderror</div>
          </div>
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
                <input type="number" min="-90" max="90" step="any" id="latitude" name="latitude" placeholder="-0.1268141"
                        class="form-control {{ $errors->has('latitude') ? 'is-invalid' : '' }}"
                        value="{{ old('latitude', isset($board) ? $board->latitude : '') }}" />
                <div class="invalid-feedback">@error('latitude') {{ $message }} @else Invalid latitude - must be between -90 and 90 @enderror</div>
              </div>
              <label for="longitude">Lon:</label>
              <div class="col-md-2">
                <input type="number" min="-180" max="180" step="any" id="longitude" name="longitude" placeholder="51.5007292"
                        class="form-control {{ $errors->has('longitude') ? 'is-invalid' : '' }}"
                        value="{{ old('longitude', isset($board) ? $board->longitude : '') }}" />
                <div class="invalid-feedback">@error('longitude') {{ $message }} @else Invalid longitude - must be between -180 and 180 @enderror</div>
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
        <div class="row form-group">
          <div class="col-6">
            @isset($board)
              <a href="{{ route('boards.details', ['board' => $board]) }}" class="btn btn-secondary btn-icon-split">
            @else
              <a href="{{ route('boards.index') }}" class="btn btn-secondary btn-icon-split">
            @endisset
              <span class="icon text-white-50"><i class="fas fa-arrow-left"></i></span>
              <span class="text">Back</span>
            </a>
          </div>
          <div class="col-6 text-right">
            <button type="submit" class="btn btn-success btn-icon-split">
              <span class="icon text-white-50"><i class="fas fa-check"></i></span>
              <span class="text">Save</span>
            </button>
          </div>
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

  function calculateBoardName(text) {
    var fullText = $('#readable_name').val();
    var boardName = _.toLower(fullText).replace(/\s/g, '-').replace(/[^a-z0-9\-]/g, '').replace(/-{2,}/g, '-');
    if (boardName == '') {
      boardName = 'my-tower';
    }
    $('#board_url').html(window.location.protocol + "{{ route('boards.index') }}/" + boardName);
  }

  $('#readable_name').on('keyup', function(event) {
    calculateBoardName();
  });
  calculateBoardName();

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
        return '<div class="tb-dropdown-option" ' +
               'data-dedication="' + item.dedication + '" ' +
               'data-county="' + item.county + '" ' +
               'data-town="' + item.town + '" ' +
               'data-area="' + item.area + '" ' +
               'data-name="' + item.name + '">' + item.name + '</div>';
      },
      item: function(item, escape) {
        return '<div class="tb-dropdown-item" ' +
               'data-dedication="' + item.dedication + '" ' +
               'data-county="' + item.county + '" ' +
               'data-town="' + item.town + '" ' +
               'data-area="' + item.area + '" ' +
               'data-name="' + item.name + '">' + item.name + '</div>';
      }
    },
    onChange: function(value) {
      var selectedOption = $('#tower')[0].selectize.getOption(value);
      $('#readable_name').val(
        selectedOption.data('town') + ' ' +
        (selectedOption.data('area') ? selectedOption.data('area') + ' ' : '') +
        selectedOption.data('dedication')
      );
      calculateBoardName();
    }
  });
</script>

@endsection
