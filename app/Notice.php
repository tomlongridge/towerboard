<?php

namespace App;

use BenSampo\Enum\Traits\CastsEnums;
use Carbon\Carbon;

use Illuminate\Database\Eloquent\Model;

use App\Enums\SubscriptionType;

class Notice extends Model
{
    use CastsEnums;
    protected $enumCasts = [
        'distribution' => SubscriptionType::class
    ];

    protected $guarded = ['id'];

    public function board()
    {
        return $this->belongsTo(Board::class);
    }

    public function createdBy()
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function replyTo()
    {
        return $this->belongsTo(User::class, 'reply_to');
    }

    public function messages()
    {
        return $this->hasMany(NoticeMessage::class);
    }

    public function scopeActive($query)
    {
        return $query
            ->whereNull('deleted_at')
            ->orWhere('deleted_at', '>', Carbon::now());
    }

    public function scopeArchived($query)
    {
        return $query
            ->whereNotNull('deleted_at')
            ->where('deleted_at', '<', Carbon::now());
    }

    public function getDeletedAtAttribute($deleted_at)
    {
        return $deleted_at != null ? new Carbon($deleted_at) : null;
    }

    public function getArchivedAttribute()
    {
        return $this->deleted_at != null && $this->deleted_at->isPast();
    }
}
