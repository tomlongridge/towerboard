@extends('boards.layout', ['title' => 'Add Members', 'activeBoard' => $board])

@section('subcontent')

  @can('update', $board)
  <div class="card shadow mb-4">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">Add Subscribers</h6>
      </div>
      <div class="card-body">
        <form method="POST" id="bulk-add-form" action="{{ route('subscriptions.bulk', ['board' => $board->name]) }}" novalidate>
          <p>Add a comma-separated list of people to add to the board. Maximum 10 at a time.</p>
          @csrf
          <div class="form-group">
            <textarea name="emails" class="form-control {{ !$errors->isEmpty() ? 'is-invalid' : '' }}" required>{{ old('emails') }}</textarea>
            <div class="invalid-feedback">@if(!$errors->isEmpty()) @foreach ($errors->all() as $error) {{ $error }} @endforeach @else Please enter at least one email address. Separate multiple addresses using a comma. @endif</div>
          </div>
          <button type="submit" class="btn btn-success btn-icon-split">
            <span class="icon text-white-50"><i class="fas fa-plus"></i></span>
            <span class="text">Add</span>
          </button>
        </form>
      </div>
    </div>
  @endcan

@endsection

@section('pagescripts')
<script>
  $('#bulk-add-form').on('submit', function(event) {
    if (this.checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.classList.add('was-validated');
  });
</script>
@endsection
