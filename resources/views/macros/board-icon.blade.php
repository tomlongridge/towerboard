@switch($board->type)
  @case(\App\Enums\BoardType::TOWER)
    <i class="fas fa-place-of-worship fa-2x {{ !$board->isSubscribed() ? 'text-gray-300' : '' }}"></i>
    @break
  @case(\App\Enums\BoardType::BRANCH)
    <i class="fas fa-sitemap fa-2x {{ !$board->isSubscribed() ? 'text-gray-300' : '' }}"></i>
    @break
  @case(\App\Enums\BoardType::GUILD)
    <i class="fas fa-sitemap fa-2x {{ !$board->isSubscribed() ? 'text-gray-300' : '' }}"></i>
    @break
  @default
    <i class="fas fa-child fa-2x {{ !$board->isSubscribed() ? 'text-gray-300' : '' }}"></i>
@endswitch
