@if ($message = Session::get($key ?? 'success'))
  <div class="alert alert-{{ $class ?? 'success' }} alert-block">
    <button type="button" class="close" data-dismiss="alert">×</button>
    <strong>{{ $content ?? $message }}</strong>
  </div>
@endif
