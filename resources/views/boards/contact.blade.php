@extends('boards.layout', ['title' => 'Contact', 'activeBoard' => $board])

@section('subcontent')

  <div class="card shadow mb-4">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">
        Contact
      </h6>
    </div>
    <div class="card-body px-5">

      <form method="POST" id="contact-form" action="{{ route('boards.contact.send', ['board' => $board]) }}" novalidate>
        @csrf

        <div class="form-group">
          <textarea class="form-control {{ $errors->has('message') ? 'is-invalid' : '' }}"
                    id="message" name="message" rows="10" placeholder="Message" required>{{ old('message') }}</textarea>
          <div class="invalid-feedback">Please enter a message to send.</div>
        </div>
        <div class="form-group">
            {!! NoCaptcha::display() !!}
            @if ($errors->has('g-recaptcha-response'))
              <div class="invalid-feedback" style="display: block">{{ $errors->first('g-recaptcha-response') }}</div>
            @endif
          </div>
        <div class="form-group">
          <button type="submit" class="btn btn-success btn-icon-split">
            <span class="icon text-white-50"><i class="fas fa-envelope"></i></span>
            <span class="text">Send</span>
          </button>
        </div>
      </form>
    </div>
  </div>

@endsection

@section('pagescripts')
{!! NoCaptcha::renderJs() !!}
<script>

  $('#contact-form').on('submit', function(event) {
    if (this.checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.classList.add('was-validated');
  });

</script>
@endsection

