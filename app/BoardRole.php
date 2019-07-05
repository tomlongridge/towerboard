<?php

namespace App;

use BenSampo\Enum\Traits\CastsEnums;

use App\Enums\RoleType;
use Illuminate\Database\Eloquent\Model;

class BoardRole extends Model
{
    use CastsEnums;

    protected $guarded = ['id'];

    protected $enumCasts = [
        'type' => RoleType::class
    ];

    public function board()
    {
        return $this->belongsTo(Board::class);
    }

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
