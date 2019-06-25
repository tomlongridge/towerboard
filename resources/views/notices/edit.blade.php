@extends('boards.layout', ['title' => isset($notice) ? 'Edit Notice' : 'Create Notice', 'activeBoard' => $board])

@section('subcontent')

    <div class="card shadow mb-4">
      <div class="card-header py-3">
        <h6 class="m-0 font-weight-bold text-primary">
          {{ isset($notice) ? 'Edit' : 'Add' }} Notice
        </h6>
      </div>
      <div class="card-body px-5">

      @isset($notice)
        <form method="POST" id="edit-form" action="{{ route('notices.update', [ 'board' => $board->name, 'notice' => $notice->id ]) }}" novalidate>
          @method('PATCH')
      @else
        <form method="POST" id="edit-form" action="{{ route('notices.store', [ 'board' => $board->name ]) }}" novalidate>
      @endisset
        @csrf

          <div class="form-group">
            <input type="text" class="form-control {{ $errors->has('title') ? 'is-invalid' : '' }}"
                   id="title" name="title" placeholder="Title"
                   value="{{ old('title', isset($notice) ? $notice->title : '') }}" required />
            <div class="invalid-feedback">Please enter a title/heading for the notice.</div>
          </div>
          <div class="form-group">
            <textarea class="form-control {{ $errors->has('body') ? 'is-invalid' : '' }}"
                      id="body" name="body" rows="10" placeholder="Notice Text"
                      required>{{ old('body', isset($notice) ? $notice->body : '') }}</textarea>
            <div class="invalid-feedback">Some text for the body of the notice is required.</div>
          </div>
          <div class="form-group">
            <input type="text" class="form-control {{ $errors->has('expires') ? 'is-invalid' : '' }}"
                   id="expires" name="expires" placeholder="Expiry date"
                   value="{{ old('expires', isset($notice) && $notice->expires ? $notice->expires->format('d/m/Y') : '') }}" />
          </div>
          <div class="form-group">
            <label for="distribution">Send To</label>
            <select name="distribution" id="distribution" class="form-control">
              @foreach (\App\Enums\SubscriptionType::getInstances() as $type)
                <option value="{{ $type->value }}"
                  {{ old('distribution', isset($notice) ? $notice->distribution : \App\Enums\SubscriptionType::getInstance(\App\Enums\SubscriptionType::BASIC)) == $type ? 'selected' : '' }} >
                  {{ ucwords(str_plural($type->description)) }}
                </option>
              @endforeach
            </select>
          </div>
          <div class="form-group">
            @isset($notice)
              <a href="{{ route('notices.show', ['board' => $board, 'notice' => $notice]) }}" class="btn btn-secondary btn-icon-split">
            @else
              <a href="{{ route('boards.show', ['board' => $board]) }}" class="btn btn-secondary btn-icon-split">
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
  $('#edit-form').on('submit', function(event) {
    if (this.checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.classList.add('was-validated');
  });

  $('#expires').datepicker({
    format: "dd/mm/yyyy",
    startDate: "{{ \Carbon\Carbon::now()->format('d/m/Y') }}",
    weekStart: 1,
    clearBtn: true,
    todayHighlight: true
  });

</script>
@endsection
